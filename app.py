from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "nexora_os_secret_key"

DB_NAME = "database.db"
UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            estado TEXT NOT NULL,
            github TEXT,
            demo TEXT,
            prioridad TEXT DEFAULT 'Media',
            fecha_limite TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto_id INTEGER NOT NULL,
            texto TEXT NOT NULL,
            completada INTEGER DEFAULT 0,
            estado TEXT DEFAULT 'Pendiente'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS archivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto_id INTEGER,
            nombre TEXT,
            ruta TEXT
        )
    """)

    conn.commit()
    conn.close()


def upgrade_db():
    conn = get_db()

    updates = [
        "ALTER TABLE proyectos ADD COLUMN usuario_id INTEGER",
        "ALTER TABLE proyectos ADD COLUMN prioridad TEXT DEFAULT 'Media'",
        "ALTER TABLE proyectos ADD COLUMN fecha_limite TEXT",
        "ALTER TABLE tareas ADD COLUMN estado TEXT DEFAULT 'Pendiente'",
        "ALTER TABLE archivos ADD COLUMN ruta TEXT"
    ]

    for sql in updates:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass

    conn.close()


def login_required():
    return "usuario_id" in session


@app.route("/")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))

    user_id = session["usuario_id"]
    conn = get_db()

    total_proyectos = conn.execute(
        "SELECT COUNT(*) FROM proyectos WHERE usuario_id = ?",
        (user_id,)
    ).fetchone()[0]

    total_tareas = conn.execute("""
        SELECT COUNT(*) FROM tareas
        JOIN proyectos ON tareas.proyecto_id = proyectos.id
        WHERE proyectos.usuario_id = ?
    """, (user_id,)).fetchone()[0]

    tareas_hechas = conn.execute("""
        SELECT COUNT(*) FROM tareas
        JOIN proyectos ON tareas.proyecto_id = proyectos.id
        WHERE proyectos.usuario_id = ? AND tareas.estado = 'Completada'
    """, (user_id,)).fetchone()[0]

    ideas = conn.execute(
        "SELECT COUNT(*) FROM proyectos WHERE usuario_id = ? AND estado = 'Idea'",
        (user_id,)
    ).fetchone()[0]

    desarrollo = conn.execute(
        "SELECT COUNT(*) FROM proyectos WHERE usuario_id = ? AND estado = 'En desarrollo'",
        (user_id,)
    ).fetchone()[0]

    publicados = conn.execute(
        "SELECT COUNT(*) FROM proyectos WHERE usuario_id = ? AND estado = 'Publicado'",
        (user_id,)
    ).fetchone()[0]

    total_archivos = conn.execute("""
        SELECT COUNT(*) FROM archivos
        JOIN proyectos ON archivos.proyecto_id = proyectos.id
        WHERE proyectos.usuario_id = ?
    """, (user_id,)).fetchone()[0]

    proyectos = conn.execute(
        "SELECT * FROM proyectos WHERE usuario_id = ? ORDER BY id DESC LIMIT 4",
        (user_id,)
    ).fetchall()

    conn.close()

    productividad = round((tareas_hechas / total_tareas) * 100) if total_tareas > 0 else 0

    return render_template(
        "dashboard.html",
        total_proyectos=total_proyectos,
        total_tareas=total_tareas,
        productividad=productividad,
        ideas=ideas,
        desarrollo=desarrollo,
        publicados=publicados,
        total_archivos=total_archivos,
        proyectos=proyectos
    )


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO usuarios (nombre, email, password) VALUES (?, ?, ?)",
                (nombre, email, password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Ese email ya está registrado"

        conn.close()
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["password"], password):
            session["usuario_id"] = usuario["id"]
            session["usuario_nombre"] = usuario["nombre"]
            return redirect(url_for("dashboard"))

        return "Email o contraseña incorrectos"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/proyectos")
def proyectos():
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    proyectos = conn.execute(
        "SELECT * FROM proyectos WHERE usuario_id = ? ORDER BY id DESC",
        (session["usuario_id"],)
    ).fetchall()
    conn.close()

    return render_template("proyectos.html", proyectos=proyectos)


@app.route("/nuevo-proyecto", methods=["GET", "POST"])
def nuevo_proyecto():
    if not login_required():
        return redirect(url_for("login"))

    if request.method == "POST":
        conn = get_db()
        conn.execute("""
            INSERT INTO proyectos
            (usuario_id, nombre, descripcion, estado, github, demo, prioridad, fecha_limite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["usuario_id"],
            request.form.get("nombre"),
            request.form.get("descripcion"),
            request.form.get("estado"),
            request.form.get("github"),
            request.form.get("demo"),
            request.form.get("prioridad"),
            request.form.get("fecha_limite")
        ))
        conn.commit()
        conn.close()

        return redirect(url_for("proyectos"))

    return render_template("nuevo_proyecto.html")


@app.route("/proyecto/<int:id>")
def proyecto_detalle(id):
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    proyecto = conn.execute(
        "SELECT * FROM proyectos WHERE id = ? AND usuario_id = ?",
        (id, session["usuario_id"])
    ).fetchone()

    if proyecto is None:
        conn.close()
        return redirect(url_for("proyectos"))

    tareas = conn.execute(
        "SELECT * FROM tareas WHERE proyecto_id = ? ORDER BY id DESC",
        (id,)
    ).fetchall()

    archivos = conn.execute(
        "SELECT * FROM archivos WHERE proyecto_id = ? ORDER BY id DESC",
        (id,)
    ).fetchall()

    pendientes = conn.execute(
        "SELECT COUNT(*) FROM tareas WHERE proyecto_id = ? AND estado = 'Pendiente'",
        (id,)
    ).fetchone()[0]

    progreso = conn.execute(
        "SELECT COUNT(*) FROM tareas WHERE proyecto_id = ? AND estado = 'En progreso'",
        (id,)
    ).fetchone()[0]

    completadas = conn.execute(
        "SELECT COUNT(*) FROM tareas WHERE proyecto_id = ? AND estado = 'Completada'",
        (id,)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "proyecto_detalle.html",
        proyecto=proyecto,
        tareas=tareas,
        archivos=archivos,
        pendientes=pendientes,
        progreso=progreso,
        completadas=completadas
    )


@app.route("/proyecto/<int:id>/editar", methods=["GET", "POST"])
def editar_proyecto(id):
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    proyecto = conn.execute(
        "SELECT * FROM proyectos WHERE id = ? AND usuario_id = ?",
        (id, session["usuario_id"])
    ).fetchone()

    if proyecto is None:
        conn.close()
        return redirect(url_for("proyectos"))

    if request.method == "POST":
        conn.execute("""
            UPDATE proyectos
            SET nombre = ?, descripcion = ?, estado = ?, github = ?, demo = ?, prioridad = ?, fecha_limite = ?
            WHERE id = ? AND usuario_id = ?
        """, (
            request.form.get("nombre"),
            request.form.get("descripcion"),
            request.form.get("estado"),
            request.form.get("github"),
            request.form.get("demo"),
            request.form.get("prioridad"),
            request.form.get("fecha_limite"),
            id,
            session["usuario_id"]
        ))
        conn.commit()
        conn.close()

        return redirect(url_for("proyecto_detalle", id=id))

    conn.close()
    return render_template("editar_proyecto.html", proyecto=proyecto)


@app.route("/proyecto/<int:id>/tarea", methods=["POST"])
def agregar_tarea(id):
    texto = request.form.get("texto")

    if texto:
        conn = get_db()
        conn.execute(
            "INSERT INTO tareas (proyecto_id, texto, estado, completada) VALUES (?, ?, 'Pendiente', 0)",
            (id, texto)
        )
        conn.commit()
        conn.close()

    return redirect(url_for("proyecto_detalle", id=id))


@app.route("/api/tarea/estado", methods=["POST"])
def api_cambiar_estado():
    data = request.get_json()

    tarea_id = data.get("tarea_id")
    estado = data.get("estado")

    completada = 1 if estado == "Completada" else 0

    conn = get_db()
    conn.execute(
        "UPDATE tareas SET estado = ?, completada = ? WHERE id = ?",
        (estado, completada, tarea_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/tarea/<int:id>/estado/<estado>/<int:proyecto_id>")
def cambiar_estado_tarea(id, estado, proyecto_id):
    completada = 1 if estado == "Completada" else 0

    conn = get_db()
    conn.execute(
        "UPDATE tareas SET estado = ?, completada = ? WHERE id = ?",
        (estado, completada, id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("proyecto_detalle", id=proyecto_id))


@app.route("/tarea/<int:id>/eliminar/<int:proyecto_id>")
def eliminar_tarea(id, proyecto_id):
    conn = get_db()
    conn.execute("DELETE FROM tareas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("proyecto_detalle", id=proyecto_id))


@app.route("/proyecto/<int:id>/upload", methods=["POST"])
def subir_archivo(id):
    if not login_required():
        return redirect(url_for("login"))

    archivo = request.files.get("archivo")

    if archivo and archivo.filename != "":
        filename = secure_filename(archivo.filename)
        ruta = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        archivo.save(ruta)

        conn = get_db()
        conn.execute(
            "INSERT INTO archivos (proyecto_id, nombre, ruta) VALUES (?, ?, ?)",
            (id, filename, ruta)
        )
        conn.commit()
        conn.close()

    return redirect(url_for("proyecto_detalle", id=id))


@app.route("/uploads/<filename>")
def ver_archivo(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/proyecto/<int:id>/eliminar")
def eliminar_proyecto(id):
    conn = get_db()
    conn.execute("DELETE FROM tareas WHERE proyecto_id = ?", (id,))
    conn.execute("DELETE FROM archivos WHERE proyecto_id = ?", (id,))
    conn.execute(
        "DELETE FROM proyectos WHERE id = ? AND usuario_id = ?",
        (id, session["usuario_id"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("proyectos"))


@app.route("/proyecto/<int:id>/ia/<tipo>")
def ia_tools(id, tipo):
    conn = get_db()
    proyecto = conn.execute(
        "SELECT * FROM proyectos WHERE id = ?",
        (id,)
    ).fetchone()
    conn.close()

    if tipo == "tareas":
        resultado = f"""Tareas sugeridas para {proyecto['nombre']}:
1. Definir funcionalidades principales.
2. Diseñar interfaz visual.
3. Crear base de datos.
4. Programar backend.
5. Probar errores.
6. Publicar versión online."""

    elif tipo == "roadmap":
        resultado = f"""Roadmap para {proyecto['nombre']}:
Fase 1: MVP funcional.
Fase 2: Diseño premium.
Fase 3: Uploads y analytics.
Fase 4: PWA.
Fase 5: Deploy online."""

    elif tipo == "linkedin":
        resultado = f"""🚀 Estoy trabajando en {proyecto['nombre']}

{proyecto['descripcion']}

Este proyecto me está ayudando a mejorar en desarrollo web, organización de productos digitales y construcción de soluciones reales.

#Python #Flask #WebDevelopment #Developer #Tech"""

    else:
        resultado = "IA no disponible."

    return render_template("ia_resultado.html", proyecto=proyecto, resultado=resultado)


@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")


@app.route("/service-worker.js")
def service_worker():
    return send_from_directory("static", "service-worker.js")


if __name__ == "__main__":
    init_db()
    upgrade_db()
    app.run(debug=True)