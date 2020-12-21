from iot_device import Config


def main():


    print("\nUID --> Hostname:")
    uid = [ 'c7:9d:75:c8:7a:14:1d:b6', '30:ae:a4:1a:2c:3c', 'weird:uid:09:07:44' ]
    for u in uid:
        print("  {:40}  {}".format(u, Config.get_device(u, 'name')))


    print("Queries:")
    queries = [
        ('project_includes', None),
        ('server_port', '1234'),
        ('advertise_port', 'none ????'),
        ('device_scan_interval', None),
        ('alsfkj fasdlkfj ', 'surely not defined!')
    ]
    for q in queries:
        print("  {:20}  {}".format(q[0], Config.get(*q)))

    print("\nDoc:")
    print(Config.get('device_scan_interval', 'no doc', attribute='doc'))

    print("\nAll configuration values:")
    for k, v in Config.get_config().items():
        print("  {:20}  {}".format(k, v))

    print("\nDevices:")
    for k,v in Config.get_config('devices.py')['devices'].items():
        print(f"  {k:20} -> {v}")

    print("\nHostname --> UID:")
    queries = [ 'esp32', 'nrf52', 'stm32', 'ble', 'hello_world' ]
    for q in queries:
        print("uid   {:20} {}".format(q, Config.get_device(q, 'uid')))
    print()
    for q in queries:
        print("proj  {:20} {}".format(q, Config.get_device(q, 'projects')))

    print("\nUID --> Hostname:")
    uid = [ 'c7:9d:75:c8:7a:14:1d:b6', '30:ae:a4:1a:2c:3c', 'weird:uid:09:07:44' ]
    for u in uid:
        print("  {:40}  {}".format(u, Config.get_device(u, 'name')))


if __name__ == "__main__":
    main()
