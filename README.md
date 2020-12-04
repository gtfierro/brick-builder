# CSV-to-Brick

**Note: the Reconciliation API server implementation has moved to a [dedicated repo](https://github.com/BrickSchema/reconciliation-api), and a publicly available server is online at http://reconciliation.brickschema.org/reconcile**

This is a small script to define Brick models from CSV files through the use of simple templates. At a high level, a CSV file contains entity names (the equipment, points and locations in a building), and a template encodes the Brick types of those entities and the relationships between them.

### Simple Example (1)

Consider the following template:

```
brick = https://brickschema.org/schema/1.1/Brick#
rdf = http://www.w3.org/1999/02/22-rdf-syntax-ns#
bldg = http://example.org/building#

bldg:$1 rdf:type brick:AHU
bldg:$1 brick:hasPoint bldg:$3
bldg:$3 rdf:type bldg:$2
```

The first 3 lines of the template define some shortcuts that can be used later in the template and in the CSV files; the item on the left of the `=` is the "namespace prefix" and the item on the right of the `=` is the "namespace URI".
The first line tells the system that `brick` will be used as a shortcut for the full Brick namespace `https://brickschema.org/schema/1.1/Brick#`.
The second line performs a similar function for the `rdf` namespace.
The third line defines a namespace for the building entities.


The last 3 lines of the file encode the RDF triples that will define the Brick model. This is the actual **template**.
The model builder will substitute in each row of a CSV file into this template and create the resulting triples.


Consider the following CSV file example (the headers are purely annotations -- they carry no semantic meaning to the tool and are optional)

| AHU | Point Class | Point Name |
|-----|-------------|------------|
| `ahu1a` | `brick:Outside_Air_Temperature_Sensor` | `oat_1` |
| `ahu1a` | `brick:Return_Air_Temperature_Sensor` | `rat_1` |


Applying the template to this CSV file results in the following triples:

```
# from the first data row of the CSV file
bldg:ahu1a  rdf:type    brick:AHU .
bldg:ahu1a  brick:hasPoint bldg:oat_1 .
bldg:oat_1  rdf:type brick:Outside_Air_Temperature_Sensor .
    
# from the second data row of the CSV file
bldg:ahu1a  rdf:type    brick:AHU .
bldg:ahu1a  brick:hasPoint bldg:rat_1 .
bldg:rat_1  rdf:type brick:Return_Air_Temperature_Sensor .
```

*Note that lines 1 and 4 are duplicate --- all duplicate lines will be handled appropriately in the output*

Which in turn generates the following Turtle file

```turtle
@prefix bldg: <http://example.org/building#> .
@prefix brick: <https://brickschema.org/schema/1.1/Brick#> .

bldg:ahu1a a brick:AHU ;
    brick:hasPoint bldg:oat_1,
        bldg:rat_1 .

bldg:oat_1 a brick:Outside_Air_Temperature_Sensor .

bldg:rat_1 a brick:Return_Air_Temperature_Sensor .
```

### Simple Example (2)

Template:

```
bldg:$1 rdf:type brick:VAV .
bldg:$1 brick:hasPoint bldg:$2 .
bldg:$2 rdf:type brick:Temperature_Sensor .
bldg:$1 brick:hasPoint bldg:$3 .
bldg:$3 rdf:type brick:Temperature_Setpoint .
$4? bldg:$1 rdf:type brick:RVAV .
```

CSV file:

```
VAV name, temperature sensor, temperature setpoint, has_reheat
A, A_ts, A_sp, false
B, B_ts, B_sp, true
```

Produces:

```turtle
@prefix bldg: <http://example.org/building#> .
@prefix brick: <https://brickschema.org/schema/1.1/Brick#> .

bldg:A a brick:VAV ;
    brick:hasPoint bldg:A_sp,
        bldg:A_ts .

bldg:B a brick:RVAV,
        brick:VAV ;
    brick:hasPoint bldg:B_sp,
        bldg:B_ts .

bldg:A_sp a brick:Temperature_Setpoint .

bldg:A_ts a brick:Temperature_Sensor .

bldg:B_sp a brick:Temperature_Setpoint .

bldg:B_ts a brick:Temperature_Sensor .
```


## Template Rules

Templates are intentionally simple while retaining a good deal of flexibility. There are essentially 3 kinds of lines that can go into a template.

1. **Namespace definition**: 
   
    ```
    pfx = namespace
    ```
    
    Many RDF terms have long URIs that point to documentation or additional information about a term, e.g. `https://brickschema.org/schema/1.1/Brick#VAV`. It is often helpful to abbreviate these long URIs using "prefixes"
    
    Examples:

    ```
    brick = https://brickschema.org/schema/1.1/Brick#
    rdf = http://www.w3.org/1999/02/22-rdf-syntax-ns#
    bldg = http://example.org/building#
    ```

2. **Triple definition**:
    
    ```
    S P O
    ```
    
    where `S`, `P` and `O` can be any one of a "slot" (e.g. `$1`) or a "uri" (e.g. `brick:Temperature_Sensor`). Recall that `S` and `O` will be things or concepts, and `P` is the relationship between them. 
    
    Each triple definition will be run on each line of the input CSV, and will generate 1 triple each. A "uri" in the position of `S`, `P` or `O` will be replicated in the output triple. A "slot" in the position of `S`, `P` or `O` will fill in the corresponding column of the current row into that slot. For example `$1` will substitute the first column of every row into the output triple
    
    Examples:

    ```
    $1 rdf:type brick:VAV
    $1 brick:hasPoint $2
    ```

3. **Conditional Triple Definition**:

    ```
    C? S P O
    ```
    
    where the prefix `C?` is a "slot" (e.g. `$2`), and `S P O` is a triple definition as above. This rule only generates the triple defined by `S P O` if the value of the column identified by `C` has a value of `true`. This can be used to help specialize types or handle other simple conditional cases:
    
    Examples:
    
    ```
    $4? $1 rdf:type brick:VAV
    $2? $2 brick:hasPoint $3
    ```
