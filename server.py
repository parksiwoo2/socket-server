import socket
from datetime import datetime
from email.parser import BytesParser
from email.policy import default
from pathlib import Path


ROOT = Path(__file__).resolve().parent
(ROOT / "request").mkdir(exist_ok=True)
(ROOT / "images").mkdir(exist_ok=True)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 8000))
    server.listen()
    print("서버 실행: http://127.0.0.1:8000", flush=True)

    while True:
        client, address = server.accept()
        with client:
            request = b""
            while b"\r\n\r\n" not in request:
                chunk = client.recv(4096)
                if not chunk:
                    break
                request += chunk
            if b"\r\n\r\n" not in request:
                continue

            header, body = request.split(b"\r\n\r\n", 1)
            headers = BytesParser(policy=default).parsebytes(
                header.split(b"\r\n", 1)[1] + b"\r\n\r\n"
            )
            if headers.get("Expect", "").lower() == "100-continue":
                client.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")

            length = int(headers.get("Content-Length", 0))
            while len(body) < length:
                chunk = client.recv(min(65536, length - len(body)))
                if not chunk:
                    break
                body += chunk

            name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            raw_file = ROOT / "request" / f"{name}.bin"
            raw_file.write_bytes(header + b"\r\n\r\n" + body)
            print(f"요청 저장: {raw_file}", flush=True)

            message = BytesParser(policy=default).parsebytes(
                header.split(b"\r\n", 1)[1] + b"\r\n\r\n" + body
            )
            for part in message.iter_parts():
                if part.get_param("name", header="content-disposition") == "image":
                    filename = Path(part.get_filename() or "image.bin").name
                    image_file = ROOT / "images" / f"{name}-{filename}"
                    image_file.write_bytes(part.get_payload(decode=True))
                    print(f"이미지 저장: {image_file}", flush=True)

            client.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
                b"Content-Length: 5\r\nConnection: close\r\n\r\nSaved"
            )