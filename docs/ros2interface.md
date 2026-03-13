
# ROS2 Interface Exporter (`ros2interface`)

Exports a VSS model to a ROS2 interface package: generates `.msg` files (per leaf or aggregated by parent branch) and optional `.srv` files for Get/Set operations.
This exporter plugs into the `vspec export` CLI like other vss-tools exporters. For generic exporter usage and common arguments, see the `vspec` documentation.

## Generated Output Structure
```
\<output>
└── <package-name>
    ├── msg  # generated .msg definitions
    |   └── \<MSG>.msg
    └── srv  # generated .srv (if setting is enabled)
        ├── Get\<MSG>.srv
        └── Set\<MSG>.srv
```

**Example Output**

```
OutputFolder
└── Vss-Interface
    ├── msg
    |   └── VehicleSpeed.msg
    └── srv
        ├── GetVehicleSpeed.srv
        └── SetVehicleSpeed.srv
```

- .msg files include VSS metadata as comments (description, unit, min/max, allowed values).
- Optional .srv files (Get\<Msg>.srv, Set\<Msg>.srv) that either nest the generated message or flatten its fields.


## Datatypes mapping between VSS and ROS2 Interface

| VSS    | ROS2           |
|--------|----------------|
| boolean| bool           |
| uint8  | uint8          |
| int8   | int8           |
| uint16 | uint16         |
| int16  | int16          |
| uint32 | uint32         |
| int32  | int32          |
| uint64 | uint64         |
| int64  | int64          |
| float  | float32        |
| double | float64        |
| string | string         |


## Command Options

### Core

- `--output <dir>`: Output directory (required).
- `--package-name <name>`: Name of generated ROS 2 interface package (default: `vss_interfaces`).
- `--mode {aggregate, leaf}`:
  - `aggregate`: one `.msg` per direct parent branch containing all of its leaf signals.
  - `leaf`: one `.msg` per leaf signal.
- `--srv {get, set, both}`: Also generate `.srv` files.
  - `get`:
    - creates Get<MSG>.srv files to retrieve data within a specified start and end time.
  - `set`:
    - creates Set<MSG>.srv files to send the data and get true as response if the data gets saved.
  - `both`:
    - creates both the Get<MSG>.srv and Set<MSG>.srv files
- `--srv-use-msg / --no-srv-use-msg`: In services, use the generated message as a nested field (default: `--srv-use-msg`); otherwise flatten fields.
- `--timestamp-mode {simple, struct}`:
  - `simple` (default): message timestamp as `uint64 timestamp`; Get request uses `uint64 start_time_ms/end_time_ms`.
  - `struct`: message timestamp uses `int64 timestamp_seconds` + `int64 timestamp_nanoseconds`; Get request uses seconds/nanoseconds pairs.
- `--timestamp-vspec <file>`: Optional VSS file containing a custom timestamp struct definition. When `--timestamp-mode struct` is set, the schema defined in this file is used to generate timestamp fields in `.msg` and `.srv` files. If omitted, the exporter auto-detects a `Timestamp` struct from the vspec include path or falls back to built-in defaults.
- `--output-vspec <file>`: Optional path to write a transformed VSS model where each selected signal is converted to a struct with:
  - `<Signal>`: `type: struct`
  - `<Signal>.time`: `type: property`, `datatype: VehicleDataTypes.Timestamp` — references the shared canonical timestamp type declared in `VehicleDataTypes.vspec`.
  - `<Signal>.value`: carries the original signal datatype, unit, min/max, and description.

### Topic/Signal Selection

- `--topics PATTERN` (repeatable): Include filter patterns.
- `--exclude-topics PATTERN` (repeatable): Exclude filter patterns.
- `--topics-file <file>`: File with one pattern per line; `#` starts a comment.
- `--topics-case-insensitive / --topics-case-sensitive`: Case-insensitive matching (default: `--topics-case-sensitive`).

**Pattern syntax**

Following patterns are supported:

- Exact FQN: `Vehicle.Speed`
- Leaf name: `Speed`
- Glob: `Vehicle.*.Speed`, `*.Speed`
- Explicit prefix`:
  - regex: `^Vehicle\.Body\..*$`
  - glob: `*.Speed`
  - fqn: `Vehicle.Speed` (exact or prefix match)
  - Name: `Speed`

## Output

### Messages (`.msg`)

- `Aggregate` mode
  one message per direct parent branch. Fields include a leading timestamp representation (`uint64 timestamp` in `simple`, or `timestamp_seconds`/`timestamp_nanoseconds` in `struct`), then one field per child leaf.

- `Leaf` mode
  one message per leaf. Fields include a timestamp representation and one field for the leaf value.

**Example — `simple` timestamp (`VehicleSpeed.msg`)**
```
# Auto-generated from VSS by vss-tools (ros2interface exporter)
# Signal: Vehicle.Speed
uint64 timestamp

# Vehicle speed.; unit=km/h
float32 speed
```

**Example — `struct` timestamp (`VehicleSpeed.msg`)**
```
# Auto-generated from VSS by vss-tools (ros2interface exporter)
# Signal: Vehicle.Speed
int64 timestamp_seconds
int64 timestamp_nanoseconds

# Vehicle speed.; unit=km/h
float32 speed
```

### Services (`.srv`)

Generated when `--srv get|set|both` is used.

- `Get<Msg>.srv`
  - Request:
    - `simple`: `uint64 start_time_ms`, `uint64 end_time_ms`
    - `struct`: `int64 start_time_seconds`, `int64 start_time_nanoseconds`, `int64 end_time_seconds`, `int64 end_time_nanoseconds`
  - Response: `<Msg>[] data` (with `--srv-use-msg`) or flattened fields

- `Set<Msg>.srv`
  - Request: `<Msg> data` (with `--srv-use-msg`) or flattened fields
  - Response: `bool success`, `string message`

### Transformed VSS (`.vspec`) — `--output-vspec`

When `--output-vspec <file>` is provided, a transformed VSS model is written alongside the ROS2 package. Each selected signal is restructured as:

```yaml
# Branch intermediaries are preserved
Vehicle:
  type: branch

Vehicle.Speed:
  type: struct

Vehicle.Speed.time:
  type: property
  datatype: VehicleDataTypes.Timestamp   # references the canonical type in VehicleDataTypes.vspec

Vehicle.Speed.value:
  type: sensor
  datatype: float
  description: Vehicle speed.
  unit: km/h
```

The `VehicleDataTypes.Timestamp` struct (declared in `VehicleDataTypes.vspec` / `spec/include/Timestamp.vspec`) is **not** re-emitted in the output — it is expected to already be part of the VSS model.
```

## Examples

```bash
# Export only Vehicle.Speed as leaf message + get/set services (simple timestamp):
vspec export ros2interface \
  --vspec spec/VehicleSignalSpecification.vspec \
  -I spec \
  --output ./out \
  --package-name vss_speed_interfaces \
  --mode leaf \
  --srv both --srv-use-msg \
  --topics Vehicle.Speed

# Export all *.Speed signals, aggregated by their parent branches:
vspec export ros2interface \
  --vspec spec/VehicleSignalSpecification.vspec \
  -I spec \
  --output ./out \
  --package-name vss_speed_agg \
  --mode aggregate \
  --srv get \
  --topics '*.Speed'

# Export with struct-based timestamp fields (auto-detected from spec include path):
vspec export ros2interface \
  --vspec spec/VehicleSignalSpecification.vspec \
  -I spec \
  --output ./out \
  --package-name vss_interfaces \
  --mode leaf \
  --srv both \
  --timestamp-mode struct

# Export with struct timestamp and a custom Timestamp.vspec schema:
vspec export ros2interface \
  --vspec spec/VehicleSignalSpecification.vspec \
  -I spec \
  --output ./out \
  --package-name vss_interfaces \
  --mode leaf \
  --srv both --srv-use-msg \
  --timestamp-mode struct \
  --timestamp-vspec path/to/Timestamp.vspec

# Export with struct timestamp and write a transformed VSS model.
# Each signal becomes <Signal>.time (datatype: VehicleDataTypes.Timestamp)
# and <Signal>.value carrying the original datatype.
# VehicleDataTypes.Timestamp is NOT re-emitted — it must already exist in the VSS model.
vspec export ros2interface \
  --vspec spec/VehicleSignalSpecification.vspec \
  -I spec \
  --output ./out \
  --package-name vss_interfaces \
  --mode leaf \
  --timestamp-mode struct \
  --output-vspec ./out/transformed.vspec
```

**Full example using the `vehicle_signal_specification` repo side-by-side with `vss-tools`:**

> Assumes the following folder layout:
> ```
> <parent-folder>/
> ├── vehicle_signal_specification/
> └── vss-tools/
> ```
> Adjust paths accordingly if your layout differs.

```bash
vspec export ros2interface \
  --vspec ../vehicle_signal_specification/spec/VehicleSignalSpecification.vspec \
  -I ../vehicle_signal_specification/spec/include \
  --types ../vehicle_signal_specification/spec/VehicleSignalSpecification.vspec \
  -q ../vehicle_signal_specification/spec/quantities.yaml \
  -u ../vehicle_signal_specification/spec/units.yaml \
  --output ./output \
  --package-name vss_speed_interfaces \
  --mode leaf \
  --timestamp-mode struct \
  --srv both --srv-use-msg \
  --topics Vehicle.Speed \
  --output-vspec ./out/transformed.vspec
```

## Usage

```bash
vspec export ros2interface \
  --vspec spec/VehicleSignalSpecification.vspec \
  -I spec \
  --output ./out \
  --package-name vss_interfaces \
  --mode aggregate|leaf \
  --srv get|set|both \
  [--srv-use-msg | --no-srv-use-msg] \
  [--timestamp-mode simple|struct] \
  [--timestamp-vspec path/to/Timestamp.vspec] \
  [--topics PATTERN ...] \
  [--exclude-topics PATTERN ...] \
  [--topics-file patterns.txt] \
  [--topics-case-insensitive] \
  [--output-vspec transformed.vspec]
```
