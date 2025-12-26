import psycopg2
import os
import dotenv
import sshtunnel

dotenv.load_dotenv()

IS_PRODUCTION = os.getenv("IS_PRODUCTION")
SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = os.getenv("SSH_PORT")
SSH_USER = os.getenv("SSH_USER")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

if (IS_PRODUCTION == "False"):
    with sshtunnel.SSHTunnelForwarder(
        (SSH_HOST, int(SSH_PORT)),
        ssh_password=SSH_PASSWORD,
        ssh_username=SSH_USER,
        remote_bind_address=(DB_HOST, int(DB_PORT))
    ) as server:
        print(f"Tunnel opened on port: {server.local_bind_port}")

        conn = psycopg2.connect(
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=DB_HOST,
            port=int(DB_PORT)
        )

        cur = conn.cursor()
        cur.execute("SELECT version();")
        print("Connected to:", cur.fetchone())

        cur.close()
        conn.close()
