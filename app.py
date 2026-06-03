import argparse
import socket
import threading
import time
import webbrowser

from worldpanel_qc.web import serve


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Worldpanel Data QC Assistant")
    parser.add_argument("--intranet", action="store_true", help="Allow colleagues on the company intranet to connect.")
    parser.add_argument("--host", help="Override the listening address.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically.")
    args = parser.parse_args(argv)
    if not args.host:
        args.host = "0.0.0.0" if args.intranet else "127.0.0.1"
    return args


def local_ipv4_addresses() -> list[str]:
    addresses = set()
    try:
        for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = result[4][0]
            if not address.startswith("127."):
                addresses.add(address)
    except OSError:
        pass
    return sorted(addresses)


def access_urls(host: str, port: int, addresses: list[str] | None = None) -> list[str]:
    if host not in {"0.0.0.0", "::"}:
        return [f"http://{host}:{port}"]
    lan_addresses = [address for address in (addresses or local_ipv4_addresses()) if not address.startswith("127.")]
    return [f"http://127.0.0.1:{port}", *[f"http://{address}:{port}" for address in lan_addresses]]


if __name__ == "__main__":
    options = parse_args()
    urls = access_urls(options.host, options.port)
    print("Worldpanel Data QC Assistant access URLs:")
    for url in urls:
        print(f"  {url}")
    if not options.no_browser:
        threading.Thread(target=lambda: (time.sleep(0.7), webbrowser.open(urls[0])), daemon=True).start()
    serve(options.host, options.port)
