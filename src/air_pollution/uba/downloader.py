import sys
from air_pollution.uba import UBAClient

def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv

    client = UBAClient()
    res = client.get_components()
    print(res.data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
