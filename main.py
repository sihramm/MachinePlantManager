# -*- coding: utf-8 -*-
import psycopg2
import psycopg2.extras
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Параметры подключения к БД (замени на свои)
DB_HOST = 'localhost'
DB_NAME = 'transport'  # твоя база данных
DB_USER = 'postgres'
DB_PASSWORD = ''  # ЗАМЕНИ НА СВОЙ ПАРОЛЬ!
DB_PORT = '5432'

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        client_encoding='UTF8'
    )
    conn.autocommit = False  # ручное управление транзакциями
    print("Подключение к БД успешно!")
except Exception as e:
    print(f"Ошибка подключения: {e}")
    exit(1)


def run_query(sql, params=None):
    """Выполняет SQL-запрос с автоматическим откатом прерванной транзакции"""
    try:
        # Если транзакция в состоянии ошибки - откатываем
        if conn.closed == 0:
            conn.rollback()

        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur
    except psycopg2.Error as e:
        conn.rollback()
        raise e


# ==================== ЗАДАНИЕ 1: Отчёт по объёму производства ====================
class Task1Frame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)

        frame_filter = ttk.Frame(self)
        frame_filter.pack(pady=10)
        ttk.Label(frame_filter, text="Год (необязательно):").pack(side=tk.LEFT, padx=5)
        self.entry_year = ttk.Entry(frame_filter, width=10)
        self.entry_year.pack(side=tk.LEFT, padx=5)
        self.btn_run = ttk.Button(frame_filter, text="Сформировать", command=self.build_report)
        self.btn_run.pack(side=tk.LEFT, padx=10)

        # Дерево для таблицы
        self.tree = ttk.Treeview(self, columns=("product", "month", "volume"), show="headings")
        self.tree.heading("product", text="Продукция")
        self.tree.heading("month", text="Месяц")
        self.tree.heading("volume", text="Объём, шт")
        self.tree.column("product", width=200)
        self.tree.column("month", width=100)
        self.tree.column("volume", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.label_total = ttk.Label(self, text="")
        self.label_total.pack(pady=5)

    def build_report(self):
        try:
            year = self.entry_year.get().strip()
            year = int(year) if year else None

            sql = """
                SELECT 
                    p.name AS product_name,
                    TO_CHAR(pr.production_date, 'Month') AS month_name,
                    COALESCE(SUM(pr.quantity), 0) AS volume
                FROM product p
                LEFT JOIN production pr ON p.product_id = pr.product_id
                WHERE (%s IS NULL OR EXTRACT(YEAR FROM pr.production_date) = %s)
                  AND (pr.status IS NULL OR pr.status = 'Успешно')
                GROUP BY p.name, TO_CHAR(pr.production_date, 'Month'), EXTRACT(MONTH FROM pr.production_date)
                ORDER BY p.name, EXTRACT(MONTH FROM pr.production_date)
            """
            cur = run_query(sql, (year, year))
            rows = cur.fetchall()
            cur.close()

            # Очистка дерева
            for item in self.tree.get_children():
                self.tree.delete(item)

            total = 0
            for row in rows:
                self.tree.insert("", tk.END, values=(row[0], row[1].strip(), row[2]))
                total += row[2]

            self.label_total.config(text=f"Общий объём производства: {total:.2f} шт.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при выполнении запроса:\n{e}")
            conn.rollback()


# ==================== ЗАДАНИЕ 2: Сводная таблица ====================
# ==================== ЗАДАНИЕ 2: Сводная таблица (исправленная) ====================
class Task2Frame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)

        frame_filter = ttk.Frame(self)
        frame_filter.pack(pady=10)
        ttk.Label(frame_filter, text="Год (необязательно):").pack(side=tk.LEFT, padx=5)
        self.entry_year = ttk.Entry(frame_filter, width=10)
        self.entry_year.pack(side=tk.LEFT, padx=5)
        self.btn_run = ttk.Button(frame_filter, text="Сформировать", command=self.build_pivot)
        self.btn_run.pack(side=tk.LEFT, padx=10)

        # Создаём Canvas с Scrollbar для таблицы
        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Горизонтальный скролл тоже добавим
        h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        self.tree = ttk.Treeview(self.canvas_frame, xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        h_scrollbar.config(command=self.tree.xview)
        v_scrollbar.config(command=self.tree.yview)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    def build_pivot(self):
        try:
            year = self.entry_year.get().strip()
            year = int(year) if year else None

            # Группируем сразу в SQL: продукт, месяц, сумма за месяц
            sql = """
                SELECT 
                    p.name AS product_name,
                    EXTRACT(MONTH FROM pr.production_date) AS month_num,
                    TO_CHAR(pr.production_date, 'Month') AS month_name,
                    SUM(pr.quantity) AS volume
                FROM product p
                JOIN production pr ON p.product_id = pr.product_id
                WHERE (%s IS NULL OR EXTRACT(YEAR FROM pr.production_date) = %s)
                  AND pr.status = 'Успешно'
                GROUP BY p.name, EXTRACT(MONTH FROM pr.production_date), TO_CHAR(pr.production_date, 'Month')
                ORDER BY p.name, month_num
            """
            cur = run_query(sql, (year, year))
            rows = cur.fetchall()
            cur.close()

            if not rows:
                messagebox.showinfo("Нет данных", "Нет данных за выбранный период")
                return

            # Собираем уникальные продукты и месяцы
            products = []
            months = {}  # {month_num: month_name}
            data = {}  # {(product, month_num): volume}

            for product, month_num, month_name, volume in rows:
                month_name = month_name.strip()
                if product not in products:
                    products.append(product)
                if month_num not in months:
                    months[month_num] = month_name
                data[(product, month_num)] = volume

            # Сортируем месяцы по номеру
            sorted_months = sorted(months.keys())
            month_names = [months[m] for m in sorted_months]

            # Настраиваем колонки
            self.tree.delete(*self.tree.get_children())
            columns = ["Продукция"] + month_names + ["Итого"]
            self.tree["columns"] = columns
            for col in columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=100, anchor=tk.CENTER)
            self.tree.column("Продукция", width=200, anchor=tk.W)

            # Заполняем строки
            grand_total = 0
            for product in products:
                row = [product]
                product_total = 0
                for month_num in sorted_months:
                    vol = data.get((product, month_num), 0)
                    row.append(vol)
                    product_total += vol
                row.append(product_total)
                self.tree.insert("", tk.END, values=row)
                grand_total += product_total

            # Строка итогов
            total_row = ["ВСЕГО"]
            for month_num in sorted_months:
                total_month = sum(data.get((p, month_num), 0) for p in products)
                total_row.append(total_month)
            total_row.append(grand_total)
            self.tree.insert("", tk.END, values=total_row, tags=('total',))

            # Подкрасим итоговую строку
            self.tree.tag_configure('total', background='lightgray')

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {e}")
            conn.rollback()

# ==================== ЗАДАНИЕ 3: График (упрощённый) ====================
class Task3Frame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)

        frame_filter = ttk.Frame(self)
        frame_filter.pack(pady=10)
        ttk.Label(frame_filter, text="Дата начала (ГГГГ-ММ-ДД):").pack(side=tk.LEFT, padx=5)
        self.entry_start = ttk.Entry(frame_filter, width=12)
        self.entry_start.pack(side=tk.LEFT, padx=5)
        ttk.Label(frame_filter, text="Дата конца:").pack(side=tk.LEFT, padx=5)
        self.entry_end = ttk.Entry(frame_filter, width=12)
        self.entry_end.pack(side=tk.LEFT, padx=5)
        self.btn_run = ttk.Button(frame_filter, text="Построить", command=self.build_chart)
        self.btn_run.pack(side=tk.LEFT, padx=10)

        self.frame_canvas = ttk.Frame(self)
        self.frame_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def build_chart(self):
        try:
            start = self.entry_start.get().strip() or None
            end = self.entry_end.get().strip() or None

            # Упрощённый запрос - только объём производства
            sql = """
                SELECT 
                    pr.production_date::DATE,
                    COALESCE(SUM(pr.quantity), 0) AS daily_volume
                FROM production pr
                WHERE (%s IS NULL OR pr.production_date >= %s::DATE)
                  AND (%s IS NULL OR pr.production_date <= %s::DATE)
                  AND (pr.status IS NULL OR pr.status = 'Успешно')
                GROUP BY pr.production_date::DATE
                ORDER BY pr.production_date::DATE
            """
            cur = run_query(sql, (start, start, end, end))
            rows = cur.fetchall()
            cur.close()

            if not rows:
                messagebox.showinfo("Нет данных", "Нет данных за выбранный период")
                return

            dates = [row[0] for row in rows]
            volumes = [float(row[1]) for row in rows]

            # Очистка старого графика
            for widget in self.frame_canvas.winfo_children():
                widget.destroy()

            fig, ax1 = plt.subplots(figsize=(8, 5))
            ax1.plot(dates, volumes, color='blue', marker='o', label='Объём производства', linewidth=2)
            ax1.set_xlabel('Дата')
            ax1.set_ylabel('Объём производства, шт', color='blue')
            ax1.tick_params(axis='y', labelcolor='blue')
            ax1.grid(True)

            title = "Динамика объёма производства"
            if start and end:
                title += f" с {start} по {end}"
            plt.title(title)
            fig.autofmt_xdate(rotation=45)
            plt.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=self.frame_canvas)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при построении графика:\n{e}")
            conn.rollback()


# ==================== ЗАДАНИЕ 4: Круговая диаграмма ====================
class Task4Frame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)

        frame_filter = ttk.Frame(self)
        frame_filter.pack(pady=10)
        ttk.Label(frame_filter, text="Год (необязательно):").pack(side=tk.LEFT, padx=5)
        self.entry_year = ttk.Entry(frame_filter, width=10)
        self.entry_year.pack(side=tk.LEFT, padx=5)
        self.btn_run = ttk.Button(frame_filter, text="Построить", command=self.build_pie)
        self.btn_run.pack(side=tk.LEFT, padx=10)

        self.frame_canvas = ttk.Frame(self)
        self.frame_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def build_pie(self):
        try:
            year = self.entry_year.get().strip()
            year = int(year) if year else None

            sql = """
                SELECT 
                    p.name AS product_name,
                    COALESCE(SUM(pr.quantity), 0) AS total_volume
                FROM product p
                LEFT JOIN production pr ON p.product_id = pr.product_id
                WHERE (%s IS NULL OR EXTRACT(YEAR FROM pr.production_date) = %s)
                  AND (pr.status IS NULL OR pr.status = 'Успешно')
                GROUP BY p.name
                ORDER BY total_volume DESC
            """
            cur = run_query(sql, (year, year))
            rows = cur.fetchall()
            cur.close()

            rows = [row for row in rows if row[1] > 0]
            if not rows:
                messagebox.showinfo("Нет данных", "Нет данных за выбранный период")
                return

            labels = [row[0] for row in rows]
            values = [float(row[1]) for row in rows]

            # Очистка старой диаграммы
            for widget in self.frame_canvas.winfo_children():
                widget.destroy()

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.pie(values, labels=labels, autopct=lambda pct: f'{pct:.1f}%\n({pct / 100 * sum(values):.0f} шт)')
            title = "Распределение объёма производства по продукции"
            if year:
                title += f" за {year} год"
            else:
                title += " за все годы"
            ax.set_title(title)
            plt.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=self.frame_canvas)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при построении диаграммы:\n{e}")
            conn.rollback()


# ==================== ГЛАВНОЕ ОКНО ====================
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MachinePlantManager - Учёт производства")
        self.root.geometry("900x700")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.notebook.add(Task1Frame(self.notebook), text="Задание 1: Отчёт по объёму")
        self.notebook.add(Task2Frame(self.notebook), text="Задание 2: Сводная таблица")
        self.notebook.add(Task3Frame(self.notebook), text="Задание 3: График")
        self.notebook.add(Task4Frame(self.notebook), text="Задание 4: Круговая диаграмма")

    def run(self):
        self.root.mainloop()
        conn.close()


if __name__ == "__main__":
    app = App()
    app.run()
