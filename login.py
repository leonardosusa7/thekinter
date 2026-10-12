import hashlib
import hmac
import tkinter as tk
from tkinter import ttk, messagebox

# --- Usuarios de ejemplo -----------------------------------------------------
# En un proyecto real esto vendría de una base de datos.
# Nunca guardes contraseñas en texto plano: se guarda salt + hash.

ITERACIONES = 200_000


def hashear(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERACIONES)


def crear_usuario(password: str, salt: bytes) -> tuple[bytes, bytes]:
    return salt, hashear(password, salt)


USUARIOS = {
    "admin": crear_usuario("1234", b"salt_admin_0001"),
    "leonardo": crear_usuario("clave_segura", b"salt_leo_0002"),
}


def validar(usuario: str, password: str) -> bool:
    datos = USUARIOS.get(usuario)
    if not datos:
        return False
    salt, hash_guardado = datos
    # compare_digest evita ataques de temporización
    return hmac.compare_digest(hash_guardado, hashear(password, salt))


# --- Ventana principal (lo que se abre tras el login) ------------------------

class VentanaPrincipal(tk.Tk):
    def __init__(self, usuario: str):
        super().__init__()
        self.title("Aplicación")
        self.geometry("500x300")
        ttk.Label(
            self, text=f"Bienvenido, {usuario}", font=("Segoe UI", 16, "bold")
        ).pack(expand=True)
        ttk.Button(self, text="Cerrar sesión", command=self.destroy).pack(pady=20)


# --- Ventana de login ---------------------------------------------------------

class Login(tk.Tk):
    MAX_INTENTOS = 3

    def __init__(self):
        super().__init__()
        self.title("Iniciar sesión")
        self.geometry("340x280")
        self.resizable(False, False)
        self.intentos = 0
        self.usuario_ok = None

        marco = ttk.Frame(self, padding=25)
        marco.pack(expand=True, fill="both")

        ttk.Label(marco, text="Iniciar sesión", font=("Segoe UI", 16, "bold")).pack(
            pady=(0, 15)
        )

        ttk.Label(marco, text="Usuario").pack(anchor="w")
        self.var_usuario = tk.StringVar()
        self.entry_usuario = ttk.Entry(marco, textvariable=self.var_usuario)
        self.entry_usuario.pack(fill="x", pady=(0, 10))

        ttk.Label(marco, text="Contraseña").pack(anchor="w")
        self.var_password = tk.StringVar()
        self.entry_password = ttk.Entry(marco, textvariable=self.var_password, show="•")
        self.entry_password.pack(fill="x")

        self.var_mostrar = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            marco,
            text="Mostrar contraseña",
            variable=self.var_mostrar,
            command=self.alternar_password,
        ).pack(anchor="w", pady=8)

        self.btn_entrar = ttk.Button(marco, text="Entrar", command=self.intentar_login)
        self.btn_entrar.pack(fill="x", pady=(5, 0))

        # Enter dispara el login desde cualquier campo
        self.bind("<Return>", lambda e: self.intentar_login())
        self.entry_usuario.focus()

    def alternar_password(self):
        self.entry_password.config(show="" if self.var_mostrar.get() else "•")

    def intentar_login(self):
        usuario = self.var_usuario.get().strip()
        password = self.var_password.get()

        if not usuario or not password:
            messagebox.showwarning("Campos vacíos", "Ingresa usuario y contraseña.")
            return

        if validar(usuario, password):
            self.usuario_ok = usuario
            self.destroy()
            return

        self.intentos += 1
        restantes = self.MAX_INTENTOS - self.intentos
        self.var_password.set("")
        self.entry_password.focus()

        if restantes <= 0:
            messagebox.showerror("Acceso bloqueado", "Demasiados intentos fallidos.")
            self.destroy()
        else:
            messagebox.showerror(
                "Error", f"Credenciales incorrectas. Intentos restantes: {restantes}"
            )


if __name__ == "__main__":
    login = Login()
    login.mainloop()

    if login.usuario_ok:
        VentanaPrincipal(login.usuario_ok).mainloop()
