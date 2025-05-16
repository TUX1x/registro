from flask import Flask, request, send_file, redirect, url_for, render_template_string
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

def init_db():
    conn = sqlite3.connect("invitados.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS invitados
                 (id TEXT PRIMARY KEY, nombre TEXT, email TEXT UNIQUE, qr TEXT, validado INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

TEMPLATE_HTML = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Registro de Invitados - Admin</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f2f2f2;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 0 15px rgba(0,0,0,0.1);
        }
        h2 {
            color: #333;
            text-align: center;
        }
        form {
            margin-bottom: 30px;
        }
        input[type="text"], input[type="email"] {
            width: calc(100% - 22px);
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 8px;
            border: 1px solid #ccc;
        }
        input[type="submit"] {
            background-color: #4CAF50;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
        }
        input[type="submit"]:hover {
            background-color: #45a049;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: center;
        }
        table, th, td {
            border: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
            padding: 10px;
        }
        td {
            padding: 8px;
        }
        .estado-ingreso {
            font-weight: bold;
        }
        .estado-ingreso.si {
            color: green;
        }
        .estado-ingreso.no {
            color: red;
        }
        .error {
            color: red;
            font-weight: bold;
            margin-top: -10px;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
<div class="container">
    <h2>Panel de Administración - Fiesta</h2>
    <form method="post">
        <input type="text" name="nombre" placeholder="Nombre completo" required><br>
        <input type="email" name="email" placeholder="Correo electrónico" required><br>
        <input type="submit" value="Registrar Invitado + Generar PDF con QR">
    </form>

    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}

    <h3>Lista de Invitados</h3>
    <table>
        <tr><th>Nombre</th><th>Correo</th><th>Estado</th><th>Acciones</th></tr>
        {% for invitado in invitados %}
        <tr>
            <td>{{ invitado[1] }}</td>
            <td>{{ invitado[2] }}</td>
            <td class="estado-ingreso {{ 'si' if invitado[4] else 'no' }}">{{ 'Ingresó' if invitado[4] else 'No ingresó' }}</td>
            <td>
                <form method="post" action="/eliminar" style="display:inline;">
                    <input type="hidden" name="id" value="{{ invitado[0] }}">
                    <input type="submit" value="Eliminar" style="background-color:#e74c3c;">
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
</div>
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def registrar():
    error = None
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]

        conn = sqlite3.connect("invitados.db")
        c = conn.cursor()
        c.execute("SELECT * FROM invitados WHERE email = ?", (email,))
        if c.fetchone():
            error = "Este correo ya está registrado."
        else:
            id_invitado = str(uuid.uuid4())
            qr_filename = f"{QR_FOLDER}/{id_invitado}.png"
            url = f"https://qr-fiesta.onrender.com/validar/{codigo}"
            qr = qrcode.make(url_qr)
            qr.save(qr_filename)

            c.execute("INSERT INTO invitados (id, nombre, email, qr) VALUES (?, ?, ?, ?)",
                      (id_invitado, nombre, email, qr_filename))
            conn.commit()

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

            conn.close()
            return send_file(pdf_filename, as_attachment=True)

        conn.close()

    conn = sqlite3.connect("invitados.db")
    c = conn.cursor()
    c.execute("SELECT * FROM invitados")
    invitados = c.fetchall()
    conn.close()
    return render_template_string(TEMPLATE_HTML, invitados=invitados, error=error)

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
        conn.close()
        return f"Acceso permitido: {nombre}"

@app.route("/eliminar", methods=["POST"])
def eliminar():
    id_invitado = request.form["id"]
    conn = sqlite3.connect("invitados.db")
    c = conn.cursor()
    c.execute("DELETE FROM invitados WHERE id = ?", (id_invitado,))
    conn.commit()
    conn.close()
    return redirect(url_for("registrar"))

if __name__ == "__main__":
    app.run(debug=True)
