import brickschema
from functools import partial
import rdflib
import csv
import re

col = re.compile(r'\$(\d+)')
sw_re = re.compile(r'\$(\d+)\?')
pfx_re = re.compile(r'(\w+)\s*=\s*(.*)$')

prefixes = {
    'brick': 'https://brickschema.org/schema/Brick#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
}


class Rule:
    def __init__(self, s, p, o, switch):
        self._repr = f"Rule<({s}, {p}, {o})>"
        self.s = self._make_mapping(s)
        self.p = self._make_mapping(p)
        self.o = self._make_mapping(o)
        if switch is not None:
            self.switch = self._make_switch(switch)
        else:
            self.switch = None

    def __repr__(self):
        return self._repr

    def _make_mapping(self, inp):
        m = col.findall(inp)
        if not len(m):
            return lambda x: inp

        def r(inp, row):
            # for each ${1,2,3,.etc} match...
            for idx in m:
                # get the value at that index
                s = row[int(idx)-1]
                if not s:
                    return None
                # substitute that value into the template (replace '$1', e.g.)
                inp = inp.replace(f"${idx}", s)
            return inp
        return partial(r, inp)

    def _make_switch(self, inp):
        m = sw_re.search(inp)
        if m is None:
            return

        def do_apply(row):
            # get the index into the row
            idx = int(m.group(1))-1
            # get the value at that index and
            # return if the value at that index is 'true'
            return row[idx].lower() == 'true'
        return do_apply

    def evaluate(self, line):
        if self.switch is not None:
            if self.switch(line):
                return (self.s(line), self.p(line), self.o(line))
            else:
                return None
        return (self.s(line), self.p(line), self.o(line))


class Builder:
    def __init__(self, rules, pfxs=None):
        self.rules = rules
        self.prefixes = prefixes.copy()
        if pfxs is not None:
            self.prefixes.update(pfxs)

    def get_triples(self, row):
        for rule in self.rules:
            t = rule.evaluate(row)
            if t is None or None in t:
                continue
            t = (
                t[0].replace(' ', '_'),
                t[1].replace(' ', '_'),
                t[2].replace(' ', '_')
            )
            triple = (
                self.apply_prefix(t[0]),
                self.apply_prefix(t[1]),
                self.apply_prefix(t[2]),
            )
            yield triple

    def apply_prefix(self, uri):
        literal = re.search(r'^"(.*)"$', uri)
        if literal is not None:
            return rdflib.Literal(literal.groups()[0])
        for pfx, ns in self.prefixes.items():
            if uri.startswith(f'{pfx}:'):
                return rdflib.URIRef(uri.replace(f'{pfx}:', ns))
        return rdflib.URIRef(uri)

    def build(self, filename, delimiter=',', has_header=False):
        g = brickschema.Graph(load_brick=False)
        for pfx, ns in self.prefixes.items():
            g.bind(pfx, ns)
        with open(filename) as f:
            csvf = csv.reader(f, delimiter=delimiter)
            if has_header:
                next(csvf)
            for row in csvf:
                row = [x.strip() for x in row]
                for triple in self.get_triples(row):
                    g.add(triple)
        return g


def parse_prefix(line):
    m = pfx_re.match(line.strip())
    if m is None:
        return
    return {m.group(1): m.group(2)}


def parse_rule(line):
    parts = re.split(r'\s+', line.strip())
    switch = None
    if len(parts) == 4:
        if not parts[0].endswith('?'):
            raise Exception("If template line has 4 parts, first part must be\
a 'switch'")
        switch = parts[0]
        parts = parts[1:]
    if len(parts) != 3:
        raise Exception(f"Line '{line}' must have 3 parts,\
separated by whitespace")
    parts = [x.strip() for x in parts]
    return Rule(parts[0], parts[1], parts[2], switch)


def parse(filename):
    rules = []
    pfxs = {}
    with open(filename) as f:
        for line in f:
            if len(line.strip()) == 0:
                continue
            pfx = parse_prefix(line)
            if pfx is not None:
                pfxs.update(pfx)
                continue
            rule = parse_rule(line)
            rules.append(rule)
    return Builder(rules, pfxs)


def generate(pairs):
    g = rdflib.Graph()
    for template_file, csv_file in pairs:
        b = parse(template_file)
        _g = b.build(csv_file, has_header=True)
        for pfx, ns in _g.namespace_manager.namespaces():
            g.bind(pfx, ns)
        g += _g
    return g


if __name__ == '__main__':
    import sys

    if len(sys.argv) == 1:
        print("""Usage:
    python make.py template1.txt:sheet1.csv template2.txt:sheet2.csv ...
""")
        sys.exit(0)

    pairs = []
    for template_pair in sys.argv[1:]:
        parts = template_pair.split(':')
        if len(parts) != 2:
            raise Exception(f"Arg '{template_pair}' needs to have form\
<template>:<csv file>")
        pairs.append(parts)

    g = generate(pairs)

    g.serialize('output.ttl', format='ttl')
