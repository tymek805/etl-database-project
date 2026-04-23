import tkinter as tk
from tkinter import messagebox
from db import SessionLocal
from models import Produkt

def create_app():
    root = tk.Tk()
    root.title("ETL Test")

    def insert_data():
        try:
            session = SessionLocal()

            produkt = Produkt(
                nazwa=entry_nazwa.get(),
                cena=int(entry_cena.get()),
                stanmagazynowy=int(entry_stan.get()),
                kategoriaid=int(entry_kategoria.get()),
                producentid=int(entry_producent.get())
            )

            session.add(produkt)
            session.commit()
            session.close()

            messagebox.showinfo("Success", "Data inserted successfully")

            entry_nazwa.delete(0, tk.END)
            entry_cena.delete(0, tk.END)
            entry_stan.delete(0, tk.END)
            entry_kategoria.delete(0, tk.END)
            entry_producent.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Label(root, text="Nazwa").grid(row=0, column=0)
    entry_nazwa = tk.Entry(root)
    entry_nazwa.grid(row=0, column=1)

    tk.Label(root, text="Cena").grid(row=1, column=0)
    entry_cena = tk.Entry(root)
    entry_cena.grid(row=1, column=1)

    tk.Label(root, text="Stan magazynowy").grid(row=2, column=0)
    entry_stan = tk.Entry(root)
    entry_stan.grid(row=2, column=1)

    tk.Label(root, text="Kategoria ID").grid(row=3, column=0)
    entry_kategoria = tk.Entry(root)
    entry_kategoria.grid(row=3, column=1)

    tk.Label(root, text="Producent ID").grid(row=4, column=0)
    entry_producent = tk.Entry(root)
    entry_producent.grid(row=4, column=1)

    submit_button = tk.Button(root, text="Submit", command=insert_data)
    submit_button.grid(row=5, column=0, columnspan=2)

    return root