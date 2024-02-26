import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import requests
from lxml import html
import threading

# Funções de Web Scraping e SQLite
def inicializar_db():
    conexao = sqlite3.connect('produtos.db')
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            url TEXT PRIMARY KEY,
            nome TEXT,
            valor REAL
        )
    ''')
    conexao.commit()
    conexao.close()

def extrair_dado(url, xpaths_valor, xpaths_nome):
    try:
        resposta = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        print(f"Status da resposta: {resposta.status_code}")  # Adicione esta linha para debug
        if resposta.status_code == 200:
            arvore = html.fromstring(resposta.content)

            valor = None
            for xpath_valor in xpaths_valor:
                resultado_valor = arvore.xpath(xpath_valor)
                if resultado_valor and resultado_valor[0].text:
                    valor = float(resultado_valor[0].text.strip().replace(',', '.'))
                    break

            nome = None
            for xpath_nome in xpaths_nome:
                resultado_nome = arvore.xpath(xpath_nome)
                if resultado_nome and resultado_nome[0].text:
                    nome = resultado_nome[0].text.strip()
                    break

            return valor, nome if nome else "Nome do produto não encontrado"
        else:
            return None, ''
    except Exception as e:
        return None, str(e)

def inserir_ou_atualizar_dados(url, nome, valor):
    conexao = sqlite3.connect('produtos.db')
    cursor = conexao.cursor()
    cursor.execute("SELECT valor FROM produtos WHERE url = ?", (url,))
    resultado = cursor.fetchone()
    if resultado:
        valor_antigo = resultado[0]
        if valor < valor_antigo:
            print("O preço diminuiu! Atualizando o valor na base de dados.")
        elif valor > valor_antigo:
            print("O preço aumentou! Atualizando o valor na base de dados.")
        cursor.execute("UPDATE produtos SET valor = ?, nome = ? WHERE url = ?", (valor, nome, url))
    else:
        print("Inserindo novo produto na base de dados.")
        cursor.execute("INSERT INTO produtos (url, nome, valor) VALUES (?, ?, ?)", (url, nome, valor))
    conexao.commit()
    conexao.close()

def atualizar_lista_produtos():
    for i in treeview.get_children():
        treeview.delete(i)
    conexao = sqlite3.connect('produtos.db')
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM produtos")
    for row in cursor.fetchall():
        treeview.insert('', 'end', values=row)
    conexao.close()

def iniciar_scraping():
    def scraping():
        loading_window = tk.Toplevel(root)
        loading_window.title("Carregando")
        centralizar_janela(loading_window, 300, 100)
        loading_label = ttk.Label(loading_window, text="Realizando scraping, por favor aguarde...")
        loading_label.pack(pady=20, padx=20)
        loading_window.update()

        url = entry_url.get()
        valor, nome = extrair_dado(url, xpaths_valor, xpaths_nome)
        if valor is not None:
            inserir_ou_atualizar_dados(url, nome, valor)
            atualizar_lista_produtos()
            messagebox.showinfo("Sucesso", "Scraping realizado com sucesso.")
        else:
            messagebox.showerror("Erro", "Não foi possível extrair os dados da URL fornecida.")

        loading_window.destroy()

    threading.Thread(target=scraping).start()

def checar_toda_base():
    def checagem():
        # Exibe uma mensagem de carregamento
        loading_window = tk.Toplevel(root)
        loading_window.title("Carregando")
        loading_label = ttk.Label(loading_window, text="Checando preços, por favor aguarde...")
        loading_label.pack(pady=20, padx=20)
        loading_window.update()

        conexao = sqlite3.connect('produtos.db')
        cursor = conexao.cursor()
        cursor.execute("SELECT url FROM produtos")
        urls = cursor.fetchall()

        alteracoes = []
        for url in urls:
            valor_atual, _ = extrair_dado(url[0], xpaths_valor, xpaths_nome)
            if valor_atual is not None:
                cursor.execute("SELECT nome, valor FROM produtos WHERE url = ?", (url[0],))
                nome, valor_almacenado = cursor.fetchone()
                if valor_atual != valor_almacenado:
                    alteracoes.append(f"{nome}: de {valor_almacenado} para {valor_atual}")
                    cursor.execute("UPDATE produtos SET valor = ? WHERE url = ?", (valor_atual, url[0]))

        conexao.commit()
        conexao.close()

        if alteracoes:
            mensagem = "\n".join(alteracoes)
        else:
            mensagem = "Não houveram alterações de preço."

        # Fecha a janela de carregamento
        loading_window.destroy()

        messagebox.showinfo("Resultados da Checagem", mensagem)
        atualizar_lista_produtos()

    threading.Thread(target=checagem).start()

def checar_produto_individual(item):
    def checagem():
        loading_window = tk.Toplevel(root)
        loading_window.title("Carregando")
        centralizar_janela(loading_window, 300, 100)
        loading_label = ttk.Label(loading_window, text="Checando produto, por favor aguarde...")
        loading_label.pack(pady=20, padx=20)
        loading_window.update()

        url = treeview.item(item, 'values')[0]
        valor_atual, nome = extrair_dado(url, xpaths_valor, xpaths_nome)
        if valor_atual is not None:
            conexao = sqlite3.connect('produtos.db')
            cursor = conexao.cursor()
            cursor.execute("SELECT nome, valor FROM produtos WHERE url = ?", (url,))
            nome, valor_almacenado = cursor.fetchone()
            if valor_atual != valor_almacenado:
                cursor.execute("UPDATE produtos SET valor = ? WHERE url = ?", (valor_atual, url))
                conexao.commit()
                mensagem = f"{nome}: preço atualizado de {valor_almacenado} para {valor_atual}"
            else:
                mensagem = f"{nome}: o preço permanece o mesmo."
            conexao.close()
            messagebox.showinfo("Checagem do Produto", mensagem)
            atualizar_lista_produtos()
        else:
            messagebox.showerror("Erro", "Não foi possível extrair os dados da URL fornecida.")

        loading_window.destroy()

    threading.Thread(target=checagem).start()

def on_item_double_click(event):
    item = treeview.selection()[0]
    checar_produto_individual(item)

def criar_menu():
    menubar = tk.Menu(root)
    menu_arquivo = tk.Menu(menubar, tearoff=0)
    menu_arquivo.add_command(label="Sair", command=root.quit)
    menubar.add_cascade(label="Arquivo", menu=menu_arquivo)

    menu_ajuda = tk.Menu(menubar, tearoff=0)
    menu_ajuda.add_command(label="Sobre")
    menubar.add_cascade(label="Ajuda", menu=menu_ajuda)

    root.config(menu=menubar)

def excluir_item_selecionado():
    item_selecionado = treeview.selection()
    
    if item_selecionado:
        resposta = messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja excluir o item selecionado?")
        
        if resposta:
            item = treeview.item(item_selecionado)
            url = item['values'][0]

            # Excluir da base de dados
            conexao = sqlite3.connect('produtos.db')
            cursor = conexao.cursor()
            cursor.execute("DELETE FROM produtos WHERE url = ?", (url,))
            conexao.commit()
            conexao.close()

            # Excluir da tabela
            treeview.delete(item_selecionado)

def centralizar_janela(janela, largura=300, altura=200):
    # Obtém as dimensões da tela
    largura_tela = janela.winfo_screenwidth()
    altura_tela = janela.winfo_screenheight()

    # Calcula a posição x e y para centralizar a janela
    x = (largura_tela // 2) - (largura // 2)
    y = (altura_tela // 2) - (altura // 2)

    # Define a posição e o tamanho da janela
    janela.geometry(f'{largura}x{altura}+{x}+{y}')

# Configuração da Janela Principal
root = tk.Tk()
root.title("Web Scraping de Produtos")
centralizar_janela(root, 1200, 600)
root.geometry("1200x600")

criar_menu()  # Cria a barra de menu

# Estilos e Layout
style = ttk.Style()
style.theme_use('clam')
style.configure("Treeview", font=("Helvetica", 12), rowheight=25)
style.configure("Treeview.Heading", font=("Helvetica", 14, 'bold'))
style.configure("TButton", font=("Helvetica", 12), padding=6)
style.configure("TLabel", font=("Helvetica", 12), padding=5)
style.configure("TEntry", font=("Helvetica", 12), padding=5)

frame_entrada = ttk.Frame(root, padding="10")
frame_entrada.pack(fill='x', expand=True)

label_url = ttk.Label(frame_entrada, text="Digite a URL do Produto:")
label_url.pack(side='left')

entry_url = ttk.Entry(frame_entrada, font=("Helvetica", 12), width=50)
entry_url.pack(side='left', expand=True, padx=10)

botao_scraping = ttk.Button(frame_entrada, text="Checar Produto", command=iniciar_scraping)
botao_scraping.pack(side='left', padx=10)

botao_checar_todos = ttk.Button(frame_entrada, text="Checar toda a base", command=checar_toda_base)
botao_checar_todos.pack(side='left')

botao_excluir = ttk.Button(frame_entrada, text="Excluir Item", command=excluir_item_selecionado)
botao_excluir.pack(side='left', padx=10)


frame_treeview = ttk.Frame(root, padding="10")
frame_treeview.pack(fill='both', expand=True)

treeview = ttk.Treeview(frame_treeview, columns=('url', 'nome', 'valor'), show='headings', selectmode='browse')
for col in ('url', 'nome', 'valor'):
    treeview.heading(col, text=col.title())
    treeview.column(col, anchor=tk.CENTER)
treeview.pack(side='left', fill='both', expand=True)
treeview.bind("<Double-1>", on_item_double_click)

# Inicialização e Loop Principal
inicializar_db()
atualizar_lista_produtos()

xpaths_valor = [
    '//*[@id="ui-pdp-main-container"]/div[1]/div/div[1]/div[2]/div[2]/div[1]/div[1]/span/span/span[2]',
    '//*[@id="price"]/div/div[1]/div[1]/span[1]/span/span[2]',
    '//*[@id="single-product"]/div/div/div[2]/div/div[1]/div[1]/span[2]' ,
    '//*[@id="blocoValores"]/div[2]/div[1]/div/h4'
]

xpaths_nome = [
    '//*[@id="ui-pdp-main-container"]/div[1]/div/div[1]/div[2]/div[1]/div/div[2]/h1',
    '//*[@id="header"]/div/div[2]/h1',
    '//*[@id="__next"]/main/article/section/div[3]/div[1]/div/h1'
]
root.mainloop()
