# coolth
Control Midea (and associated brands) smart air conditioners from Python or the command line. It reaches a device two ways: directly on your local network, or remotely through the Midea cloud. Use whichever fits, or both. Async support, minimal dependencies.

Because it can control a unit remotely, you can put the air conditioner on its own isolated network, a guest or IoT VLAN kept away from your computers and phones, and still control it from anywhere. The device never has to be reachable from your main LAN.

This is an independent fork of [mill1000/midea-msmart](https://github.com/mill1000/midea-msmart) that adds cloud control. The upstream project intentionally does not include cloud functionality, so this fork is maintained separately and is not affiliated with it.

## Supported Devices
This controls air conditioners from Midea and several associated brands that use the following Android apps or their iOS equivalents:
* Artic King (com.arcticking.ac)
* Cooper & Hunter (com.ch.air)
* Midea Air (com.midea.aircondition.obm)
* NetHome Plus (com.midea.aircondition)
* SmartHome/MSmartHome (com.midea.ai.overseas)
* Toshiba AC NA (com.midea.toshiba)
* 美的美居 (com.midea.ai.appliances)

__Note: Only air conditioners (type 0xAC and 0xCC) are supported. See the [usage](#usage) section for how to check compatibility.__

## How it connects
coolth can reach a device two ways. Pick whichever suits the situation:

* **Local network** ([usage](#usage)). Talks directly to the unit over your LAN. Fast, and needs no internet connection once set up.
* **Cloud** ([cloud control](#cloud-control)). Sends commands through the Midea cloud, so you can control a unit from anywhere, including one that is not reachable on your LAN at all.

The cloud path is what makes network isolation practical. Put the air conditioner on a guest or IoT network, keep it away from the rest of your devices, and still control it. Cloud control is currently available for AC (0xAC) devices and uses the internet for every command.

For newer "V3" devices, the local path contacts the Midea cloud once to fetch a token and key for authentication. After that, local control needs no further cloud connection. You can supply your own account credentials rather than the built in ones.

## Installing
Install with [pipx](https://pipx.pypa.io) straight from this repository:

```shell
pipx install --force git+https://github.com/a904guy/coolth-ac-controller.git
```

Re-run the same command any time to update to the latest version. The command name is `coolth`, so it will not conflict with the upstream `msmart-ng` if you also have that installed.

## Usage
### Command Line Interface (CLI)
coolth provides a command line tool for device discovery, querying, and control.

```shell
$ coolth --help
usage: coolth [-h] [-v] {discover,query,control,download} ...
```

For details on each subcommand, run `coolth <command> --help`.

#### Discover
Discover devices on the local network with `coolth discover`.

```shell
$ coolth discover
INFO:coolth.cli:Discovering all devices on local network.
...
INFO:coolth.cli:Found 1 devices.
INFO:coolth.cli:Found device:
{'ip': '10.100.1.140', 'port': 6444, 'id': 15393162840672, 'online': True, 'supported': True, 'type': <DeviceType.AIR_CONDITIONER: 172>, 'name': 'net_ac_F7B4', 'sn': '000000P0000000Q1F0C9D153F7B40000', 'key': None, 'token': None}
```

Ensure the device type is 0xAC and the `supported` property is True.

Save the device ID, IP address, and port. Version 3 devices will also need the `token` and `key` fields to control the device. The `id` field is what you use as the host for cloud control.

##### Note: V1 Device Owners
Owners of V1 devices might see this error:

```
ERROR:coolth.discover:V1 device not supported yet.
```

Please report it with the output of `coolth discover --debug`.

#### Query
Query device state and capabilities with `coolth query`.

```shell
$ coolth query <HOST>
```

Add `--capabilities` to query capabilities before requesting the state.

**Note:** Version 3 devices need either the `--auto` argument or the `--token`, `--key` and `--id` arguments to connect.

**Note:** For CC devices, either the `--auto` argument or the `--device_type` argument must be specified.

#### Control
Control a device with `coolth control`. The command takes key-value pairs of settings.

Enumerated settings like `operational_mode`, `fan_speed`, and `swing_mode` accept integer or string values, e.g. `operational_mode=cool`, `fan_speed=100`, `swing_mode=both`.

Number settings like `target_temperature` accept floating point or integer values, e.g. `target_temperature=20.5`.

Boolean settings like `display_on` and `beep` accept integer or string values, e.g. `display_on=True`, `beep=0`.

```shell
$ coolth control <HOST> operational_mode=cool target_temperature=20.5 fan_speed=100 display_on=True beep=0
```

**Note:** Version 3 devices need either the `--auto` argument or the `--token`, `--key` and `--id` arguments to connect.

**Note:** For CC devices, either the `--auto` argument or the `--device_type` argument must be specified.

#### Cloud control
Add `--cloud` to `query` or `control` to reach the device through the Midea cloud instead of the local network. This works from anywhere with internet access, so you do not need to be on the same network as the unit.

The main reason to use this is network isolation. You can put the air conditioner on a guest or IoT network, away from your computers and phones, and still control it. The unit does not need to be reachable from your LAN at all.

With `--cloud`, the host argument is the numeric appliance id, not an IP. Get the id from `coolth discover` (the `id` field) while the device is still reachable locally, or from your Midea account. You also need `--account` and `--password`.

```shell
$ coolth query 151732606158606 --cloud --account you@example.com --password secret
$ coolth control 151732606158606 --cloud --account you@example.com --password secret operational_mode=cool target_temperature=24
```

Notes:
* Cloud control is currently supported for AC (0xAC) devices.
* Cloud set commands take a few seconds to reach the unit.
* Cloud access uses one login session per account. If you run cloud commands while the phone app is open, one of them may get signed out. Use the config file below to keep credentials off the command line.

#### Config file
To avoid repeating `--account`, `--password`, and other options on every command, put them in a config file. Keys match the flag names.

coolth looks for a config file in this order:
1. the path in the `COOLTH_CONFIG` environment variable
2. `.coolth.env` in the current directory
3. `~/.config/coolth/config`

Example config file:

```ini
account = you@example.com
password = secret
host = 151732606158606
cloud = true
```

With that in place you can just run:

```shell
$ coolth query
$ coolth control operational_mode=cool target_temperature=24
```

Command line flags always override the config file. Supported keys are `account`, `password`, `region`, `host`, `cloud`, `app_id`, and `app_key`.

### Python
Control a device over the **local network**:

```python
from coolth.device import AirConditioner as AC

# Build a device
device = AC(ip=DEVICE_IP, port=6444, device_id=int(DEVICE_ID))

# Read capabilities and current state
await device.get_capabilities()
await device.refresh()

# Change settings and apply them
device.power_state = True
device.operational_mode = AC.OperationalMode.COOL
device.target_temperature = 24
await device.apply()
```

Control the same device over the **cloud**, using the identical device API. The host is the numeric appliance id, and you log in once with your account:

```python
from coolth.device import AirConditioner as AC
from coolth.cloud_lan import CloudLAN, attach

cloud = CloudLAN(APPLIANCE_ID, "you@example.com", "secret")
await cloud.login()

# Route this device through the cloud instead of the LAN
device = AC(ip="cloud", port=0, device_id=APPLIANCE_ID)
attach(device, cloud)

await device.refresh()
device.target_temperature = 24
await device.apply()
```

Discover devices on the local network:

```python
from coolth.discover import Discover

# Discover all devices on the network
devices = await Discover.discover()

# Discover a single device by IP
device = await Discover.discover_single(DEVICE_IP)
```

See [example.py](example.py) for complete runnable examples of both the local and cloud paths.

### Home Assistant
This fork renames the Python module to `coolth`, so the Home Assistant integration [midea-ac-py](https://github.com/mill1000/midea-ac-py), which imports `msmart`, is not compatible. Use the upstream project for Home Assistant.

## Troubleshooting
* If devices are not being discovered, ensure your devices are on the same subnet as your computer.
* If a cloud connection cannot be made, try a different region with `--region`, or double check the account and password.

## Gratitude
This project is an independent fork of [mill1000/midea-msmart](https://github.com/mill1000/midea-msmart), which is itself a fork of [mac-zhou/midea-msmart](https://github.com/mac-zhou/midea-msmart). It builds upon the work of
* [dudanov/MideaUART](https://github.com/dudanov/MideaUART)
* [NeoAcheron/midea-ac-py](https://github.com/NeoAcheron/midea-ac-py)
* [andersonshatch/midea-ac-py](https://github.com/andersonshatch/midea-ac-py)
* [yitsushi/midea-air-condition](https://github.com/yitsushi/midea-air-condition)
