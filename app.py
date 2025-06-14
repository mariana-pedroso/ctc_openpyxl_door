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

def converter_string_para_float(valor_str):
    """
    Converte uma string de valor monetário (antigo ou novo formato) para float.
    Detecta automaticamente o separador decimal.

    Args:
        valor_str (str): A string contendo o valor monetário.

    Returns:
        float: O valor numérico convertido.
    """
    if ',' in valor_str and '.' in valor_str:
        # Se contiver ambos, verifica qual é o separador decimal
        # Ex: 2.258,31 (formato antigo - vírgula é decimal)
        # Ex: 2,894.28 (formato novo - ponto é decimal)
        if valor_str.index(',') < valor_str.index('.'):
            # Ex: 2,894.28 -> vírgula antes do ponto, então vírgula é milhar, ponto é decimal (NOVO)
            valor_limpo = valor_str.replace(',', '') # Remove vírgula de milhar
            return float(valor_limpo)
        else:
            # Ex: 2.258,31 -> ponto antes da vírgula, então ponto é milhar, vírgula é decimal (ANTIGO)
            valor_limpo = valor_str.replace('.', '').replace(',', '.') # Remove ponto de milhar, troca vírgula por ponto decimal
            return float(valor_limpo)
    elif ',' in valor_str:
        # Só tem vírgula, assume que é separador decimal (formato antigo simplificado, ou sem milhar)
        valor_limpo = valor_str.replace('.', '').replace(',', '.')
        return float(valor_limpo)
    elif '.' in valor_str:
        # Só tem ponto, assume que é separador decimal (formato novo simplificado, ou sem milhar)
        return float(valor_str)
    else:
        # Nenhum separador, tenta converter diretamente (ex: "100")
        return float(valor_str)

def extrair_dados_ctc(texto):
    """
    Extrai os dados de Competência e Valor do texto da Certidão de Tempo de Contribuição.
    Suporta os dois formatos de valor.

    Args:
        texto (str): O texto da Certidão de Tempo de Contribuição.

    Returns:
        pandas.DataFrame: Um DataFrame com as colunas 'Competência' e 'Valor'.
    """

    # Expressão regular para encontrar as linhas de Competência e Valor
    # Alterada para capturar ambos os formatos de número:
    # (\d{1,}(?:\.\d{3})*,\d{2}) -> formato antigo (ponto milhar, vírgula decimal)
    # OU
    # (\d{1,}(?:,\d{3})*\.\d{2}) -> formato novo (vírgula milhar, ponto decimal)
    padrao = r"(\d{2}/\d{4})\s+(\d{1,}(?:(?:\.\d{3})*,\d{2}|(?:,\d{3})*\.\d{2}))"
    correspondencias = re.findall(padrao, texto)

    competencias = []
    valores = []

    for comp, valor_str in correspondencias:
        competencias.append(comp)
        valores.append(converter_string_para_float(valor_str)) # Usar a nova função de conversão

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
        # Retorna None para o caminho do arquivo e uma mensagem de erro para o Gradio
        return None, f"Ocorreu um erro ao processar os dados: {e}. Verifique o formato do texto de entrada."

# Interface Gradio
iface = gr.Interface(
    fn=processar_dados_e_salvar_excel,
    inputs=[gr.Textbox(label="Cole o texto da CTC aqui. Dúvidas, falar com Mariana.")],
    outputs=[gr.File(label="Download do arquivo Excel", file_types=[".xlsx"]), gr.Textbox(label="Mensagem")],
)

if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0", server_port=10000) #porta de acesso
