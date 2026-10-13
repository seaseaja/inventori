from sqlalchemy import create_engine, text

PG_URL = "postgresql://inventoriuser:inventoripass123@localhost:5432/db_inventori"
MYSQL_URL = "mysql+mysqlconnector://root:021936@localhost:3306/db_inventori"

pg = create_engine(PG_URL)
my = create_engine(MYSQL_URL)

# 1. Baca semua data dari PostgreSQL
with pg.connect() as src:
    rows = src.execute(text(
        "SELECT kode, nama_barang, harga_beli, harga_jual, stok FROM barang"
    )).mappings().all()

print(f"Ketemu {len(rows)} data di PostgreSQL")

# 2. Bikin tabel di MySQL (kalau belum ada) lalu masukin datanya
with my.begin() as dst:
    dst.execute(text("""
        CREATE TABLE IF NOT EXISTS barang (
            kode VARCHAR(10) PRIMARY KEY,
            nama_barang VARCHAR(100) NOT NULL,
            harga_beli DOUBLE NOT NULL,
            harga_jual DOUBLE NOT NULL,
            stok INT NOT NULL
        )
    """))

    for r in rows:
        dst.execute(text("""
            INSERT INTO barang (kode, nama_barang, harga_beli, harga_jual, stok)
            VALUES (:kode, :nama_barang, :harga_beli, :harga_jual, :stok)
            ON DUPLICATE KEY UPDATE
                nama_barang = VALUES(nama_barang),
                harga_beli  = VALUES(harga_beli),
                harga_jual  = VALUES(harga_jual),
                stok        = VALUES(stok)
        """), dict(r))

print("Selesai, data berhasil dipindah ke MySQL")