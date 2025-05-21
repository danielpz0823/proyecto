
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import pandas as pd
import os
import random
import string

app = Flask(__name__)
app.secret_key = "supersecretkey"

RESULT_FOLDER = "resultados"
if not os.path.exists(RESULT_FOLDER): os.makedirs(RESULT_FOLDER)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        email = request.form.get("email")
        df = pd.read_excel("AdminFuncionales.xlsx")
        df.columns = df.columns.str.lower()
        match = df[(df["usuario"] == usuario) & (df["email"] == email)]
        if not match.empty:
            codigo = ''.join(random.choices(string.digits, k=6))
            session["codigo_verificacion"] = codigo
            session["usuario_autenticando"] = usuario
            print(f"[DEBUG] Código enviado a {email}: {codigo}")
            flash("Código enviado (simulado)", "success")
            return redirect(url_for("verify"))
        else:
            flash("Credenciales incorrectas", "error")
    return render_template("login.html")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        codigo = request.form.get("codigo")
        if codigo == session.get("codigo_verificacion"):
            session["usuario"] = session.get("usuario_autenticando")
            return redirect(url_for("dashboard"))
        flash("Código incorrecto", "error")
    return render_template("verify.html")

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")
    try:
        file_th = request.files.get("file_th")
        file_da = request.files.get("file_da")
        if not file_th or not file_da:
            flash("Debes subir ambos archivos", "error")
            return redirect(request.url)

        path_th = os.path.join("uploads", "UsuariosTH.xlsx")
        path_da = os.path.join("uploads", "UsuariosDA.xlsx")
        os.makedirs("uploads", exist_ok=True)
        file_th.save(path_th)
        file_da.save(path_da)

        df_th = pd.read_excel(path_th)
        df_da = pd.read_excel(path_da)
        df_th.columns = df_th.columns.str.lower()
        df_da.columns = df_da.columns.str.lower()

        da_activos = df_da[df_da["estado"] == "activo"]
        th_activos = df_th[df_th["estado"] == "activo"]
        th_inactivos = df_th[df_th["estado"] == "inactivo"]

        df_cert = th_activos[th_activos["usuario"].isin(da_activos["usuario"])]
        df_incons = th_inactivos[th_inactivos["usuario"].isin(da_activos["usuario"])]

        df_cert.to_excel(os.path.join(RESULT_FOLDER, "usuarios_certificados.xlsx"), index=False)
        df_incons.to_excel(os.path.join(RESULT_FOLDER, "usuarios_inactivos_inconsistentes.xlsx"), index=False)

        # NUEVOS ARCHIVOS

        # Usuarios inactivos en ambos
        inactivos_en_ambos = df_th[
            (df_th["estado"].str.lower() == "inactivo") &
            (df_th["usuario"].isin(df_da[df_da["estado"].str.lower() == "inactivo"]["usuario"]))
        ]

        # Usuarios activos en TH pero inactivos en DA
        activos_th_inactivos_da = df_th[
            (df_th["estado"].str.lower() == "activo") &
            (df_th["usuario"].isin(df_da[df_da["estado"].str.lower() == "inactivo"]["usuario"]))
        ]

        # Guardar archivos
        inactivos_en_ambos.to_excel(os.path.join(RESULT_FOLDER, "usuarios_inactivos_en_ambos.xlsx"), index=False)
        activos_th_inactivos_da.to_excel(os.path.join(RESULT_FOLDER, "usuarios_activos_th_inactivos_da.xlsx"), index=False)


        session["resumen_certificacion"] = {
            "certificados": len(df_cert),
            "inconsistentes": len(df_incons),
            "total_th": len(df_th),
            "total_da": len(df_da),
            "inactivos_th_da": len(inactivos_en_ambos),
            "activos_th_no_en_da": len(activos_th_inactivos_da)
        }

        return redirect(url_for("resultados"))

    except Exception as e:
        flash(f"Error: {e}", "error")
        return redirect(request.url)

@app.route("/resultados")
def resultados():
    datos = session.get("resumen_certificacion", {})
    return render_template("results.html", **datos)

@app.route("/descargar/<tipo>")
def descargar(tipo):
    if tipo == "certificados":
        return send_file("resultados/usuarios_certificados.xlsx", as_attachment=True)
    elif tipo == "inconsistentes":
        return send_file("resultados/usuarios_inactivos_inconsistentes.xlsx", as_attachment=True)
    elif tipo == "inactivos_en_ambos":
        return send_file("resultados/usuarios_inactivos_en_ambos.xlsx", as_attachment=True)
    elif tipo == "activos_th_inactivos_da":
        return send_file("resultados/usuarios_activos_th_inactivos_da.xlsx", as_attachment=True)
    return "Tipo inválido", 400

if __name__ == "__main__":
    app.run(debug=True)
