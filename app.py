import gradio as gr
import logging
import pandas as pd
import re
from io import BytesIO
import tempfile

# Configurar o logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Variável global para controlar o número do arquivo a ser salvo
arquivo_contador = 1

def extrair_dados_ctc(texto):
    """
    Extrai os dados de Competência e Valor do texto da Certidão de Tempo de Contribuição.

    Args:
        texto (str): O texto da Certidão de Tempo de Contribuição.

    Returns:
        pandas.DataFrame: Um DataFrame com as colunas 'Competência' e 'Valor'.
    """

    # Expressão regular para encontrar as linhas de Competência e Valor
    padrao = r"(\d{2}/\d{4})\s+(\d{1,3},\d{2})"
    correspondencias = re.findall(padrao, texto)

    competencias = []
    valores = []

    for comp, valor in correspondencias:
        competencias.append(comp)
        valores.append(float(valor.replace(',', '.')))  # Converter para float

    df = pd.DataFrame({'Competência': competencias, 'Valor': valores})
    return df

def criar_excel_download(df):
    """
    Cria um arquivo Excel em memória para download.

    Args:
        df (pandas.DataFrame): O DataFrame com os dados a serem escritos no Excel.

    Returns:
        tuple: Uma tupla contendo os bytes do arquivo Excel e o nome do arquivo.
    """

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    output.seek(0)
    excel_bytes = output.getvalue()
    nome_arquivo = "dados_ctc.xlsx"
    return excel_bytes, nome_arquivo

def processar_dados_e_salvar_excel(texto_entrada):
    global arquivo_contador
    try:
        logging.info(f"Conteúdo do texto de entrada lido (tipo: {type(texto_entrada)}, {len(texto_entrada)} caracteres)")

        # Extrair os dados da CTC
        df_ctc = extrair_dados_ctc(texto_entrada)

        # Criar o arquivo Excel para download
        excel_bytes, nome_arquivo = criar_excel_download(df_ctc)

        # Criar um arquivo temporário para salvar os bytes do Excel
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            tmp_file.write(excel_bytes)
            tmp_file_path = tmp_file.name  # Obter o caminho do arquivo temporário

        logging.info(f"Arquivo Excel gerado com sucesso: {nome_arquivo}")
        arquivo_contador += 1
        return tmp_file_path, nome_arquivo  # Retornar o caminho do arquivo temporário

    except Exception as e:
        logging.error(f"Erro ao processar os dados: {e}")
        return None, None

# Interface Gradio
iface = gr.Interface(
    fn=processar_dados_e_salvar_excel,
    inputs=[gr.Textbox(label="Cole o texto da CTC aqui")],
    outputs=[gr.File(label="Download do arquivo Excel", file_types=[".xlsx"]), gr.Textbox(label="Mensagem")],
)

if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0", server_port=10000) #porta de acesso