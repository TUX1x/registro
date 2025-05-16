from flask import Flask, request, send_file, render_template
import qrcode
import sqlite3
import uuid
import os
from fpdf import FPDF

app = Flask(__name__)
QR_FOLDER = "qrs"
PDF_FOLDER = "pdfs"
os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

# Crear la base de datos si no existe
def init_db():
    conn = sqlite3.connect("invitados.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS invitados
                 (id TEXT PRIMARY KEY, nombre TEXT, email TEXT UNIQUE, qr TEXT, validado INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]

        # Validar si el email ya existe
        conn = sqlite3.connect("invitados.db")
        c = conn.cursor()
        c.execute("SELECT * FROM invitados WHERE email = ?", (email,))
        if c.fetchone():
            conn.close()
            return "Este correo ya está registrado. Intenta con otro."

        id_invitado = str(uuid.uuid4())
        qr_filename = f"{QR_FOLDER}/{id_invitado}.png"

        # Crear código QR con URL de validación
        url_qr = f"http://localhost:5000/validar/{id_invitado}"
        qr = qrcode.make(url_qr)
        qr.save(qr_filename)

        # Guardar en base de datos
        c.execute("INSERT INTO invitados (id, nombre, email, qr) VALUES (?, ?, ?, ?)", 
                  (id_invitado, nombre, email, qr_filename))
        conn.commit()
        conn.close()

        # Crear PDF con QR
        pdf_filename = f"{PDF_FOLDER}/{id_invitado}.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=16)
        pdf.cell(200, 10, txt="Invitación a la fiesta", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Nombre: {nombre}", ln=True)
        pdf.cell(200, 10, txt="Presenta este código en la entrada:", ln=True)
        pdf.image(qr_filename, x=60, y=60, w=90)
        pdf.output(pdf_filename)

        return send_file(pdf_filename, as_attachment=True)

    return render_template("index.html")

@app.route("/validar/<id_invitado>")
def validar(id_invitado):
    conn = sqlite3.connect("invitados.db")
    c = conn.cursor()
    c.execute("SELECT nombre, validado FROM invitados WHERE id = ?", (id_invitado,))
    row = c.fetchone()
    if not row:
        return "Código QR no válido"
    nombre, validado = row
    if validado:
        return f"{nombre} ya ingresó."
    else:
        c.execute("UPDATE invitados SET validado = 1 WHERE id = ?", (id_invitado,))
        conn.commit()
        return f"Acceso permitido: {nombre}"

if __name__ == "__main__":
    app.run(debug=True)
