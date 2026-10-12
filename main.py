from login import Login

if __name__ == "__main__":
    login = Login()
    login.mainloop()

    if login.usuario_ok:
        # ttkbootstrap se importa recién aquí, después de cerrar el login,
        # para que no cambie el estilo de la ventana de login.
        from shell import Shell

        Shell(login.usuario_ok).mainloop()
