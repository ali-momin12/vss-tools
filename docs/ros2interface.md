
# ROS 2 Interface Exporter (`ros2interface`)

Export a VSS model to a ROS 2 interface package: generates `.msg` files (per leaf or aggregated by parent branch) and optional `.srv` files for Get/Set operations.
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


## Datatypes mapping between VSS and ROS 2 Interface

| VSS    | ROS 2          |
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
  - `struct`: message timestamp uses `int32 timestamp_sec` + `uint32 timestamp_nanosec`; Get request uses sec/nanosec pairs.
- `--output-vspec <file>`: Optional path to write a transformed VSS file with:
  - shared timestamp struct schema: `Time_t`, `Time_t.t_sec`, `Time_t.t_nanosec`
  - each selected signal converted to a struct: `<Signal>.time.t_sec`, `<Signal>.time.t_nanosec`, `<Signal>.value`

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
  one message per direct parent branch. Fields include a leading timestamp representation (`uint64 timestamp` in `simple`, or `timestamp_sec`/`timestamp_nanosec` in `struct`), then one field per child leaf.

- `Leaf` mode
  one message per leaf. Fields include timestamp representation and one field for the leaf value (`value` in `struct` mode).

### Services (`.srv`)

This file is Generated when `--srv get|set|both` parameter is used. The output files are:

- `Get<Msg>.srv`
  - Request:
    - `simple`: `uint64 start_time_ms`, `uint64 end_time_ms`
    - `struct`: `int32 start_time_sec`, `uint32 start_time_nanosec`, `int32 end_time_sec`, `uint32 end_time_nanosec`
  - Response: `Msg[] data` or flattened fields

- `Set<Msg>.srv`
  - Request: `Msg data` or flattened fields
  - Response: `bool success`, `string message`

## Examples

```bash
# Export only Vehicle.Speed as leaf message + get/set services:
vspec export ros2interface   --vspec spec/VehicleSignalSpecification.vspec   -I spec   --output ./out   --package-name vss_speed_interfaces   --mode leaf   --srv both --srv-use-msg   --topics Vehicle.Speed

# Export all *.Speed signals, aggregated by their parent branches:
vspec export ros2interface   --vspec spec/VehicleSignalSpecification.vspec   -I spec   --output ./out   --package-name vss_speed_agg   --mode aggregate   --srv get   --topics '*.Speed'

# Export struct-based timestamp fields
vspec export ros2interface   --vspec spec/VehicleSignalSpecification.vspec   -I spec   --output ./out   --package-name vss_interfaces   --mode leaf   --srv both   --timestamp-mode struct

# Emit transformed VSS (shared Timestamp{seconds, nanoseconds} + <Signal>.time.seconds/<Signal>.time.nanoseconds/<Signal>.value)
vspec export ros2interface   --vspec spec/VehicleSignalSpecification.vspec   -I spec   --output ./out   --package-name vss_interfaces   --mode leaf   --timestamp-mode struct   --output-vspec ./out/transformed.vspec

# Emits transformed VSS (shared Timestamp{seconds, nanoseconds} + <Signal>.time.seconds/<Signal>.time.nanoseconds/<Signal>.value)
# while also taking into account the Timestamp.vspec tree schema.
# Note: The example below executes assuming following folder structure:
#└── <parent-project-folder>
#    ├── vehicle_signal_specification
#    └── vss-tools
# Note: if the folder structure varies or differes from what is stated above, the path used in the example below for files and directories is required to be updated.

vspec export ros2interface  --vspec ../vehicle_signal_specification/spec/VehicleSignalSpecification.vspec -I ../vehicle_signal_specification/spec/include --types ../vehicle_signal_specification/spec/VehicleSignalSpecification.vspec   --output ./output   --package-name vss_speed_interfaces  --mode leaf --timestamp-mode struct  --srv both --srv-use-msg  --topics Vehicle.Speed -q ../vehicle_signal_specification/spec/quantities.yaml -u ../vehicle_signal_specification/spec/units.yaml --output-vspec ./out/transformed.vspec

```

## Usage

```bash
vspec export ros2interface   --vspec spec/VehicleSignalSpecification.vspec   -I spec   --output ./out   --package-name vss_interfaces   --mode aggregate|leaf   --srv get|set|both   [--srv-use-msg | --no-srv-use-msg]   [--timestamp-mode simple|struct]   [--topics PATTERN ...]   [--exclude-topics PATTERN ...]   [--topics-file patterns.txt]   [--topics-case-insensitive]   [--output-vspec transformed.vspec]
```
