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
    Normaliza a string removendo separadores de milhar e garantindo ponto decimal.

    Args:
        valor_str (str): A string contendo o valor monetário.

    Returns:
        float: O valor numérico convertido.
    """
    # Remove espaços em branco extras no início/fim
    valor_str = valor_str.strip()

    # Cenário 1: Formato Novo (vírgula para milhares, ponto para decimal) - Ex: 1,031.87
    # Onde há vírgula E ponto, e o ponto é o separador decimal.
    # Ex: 1,031.87 -> 1031.87
    if ',' in valor_str and '.' in valor_str:
        # Se o último separador é um ponto, é provável que seja o formato novo
        if valor_str.rfind('.') > valor_str.rfind(','):
            valor_limpo = valor_str.replace(',', '')  # Remove vírgulas de milhar
            return float(valor_limpo)
        # Se o último separador é uma vírgula, é provável que seja o formato antigo
        # Ex: 2.258,31 -> 2258.31
        else:
            valor_limpo = valor_str.replace('.', '').replace(',', '.') # Remove pontos de milhar, troca vírgula por ponto
            return float(valor_limpo)
    
    # Cenário 2: Formato Antigo (ponto para milhares, vírgula para decimal) - Ex: 2.258,31 ou 732,47
    # Onde há vírgula, mas não ponto, ou o ponto é para milhares e a vírgula para decimal.
    # Ex: 732,47 -> 732.47
    # Ex: 2.258,31 -> 2258.31
    elif ',' in valor_str:
        valor_limpo = valor_str.replace('.', '').replace(',', '.')
        return float(valor_limpo)

    # Cenário 3: Formato simples com ponto decimal (sem separador de milhar) - Ex: 100.50
    # Ou simplesmente um número inteiro.
    elif '.' in valor_str:
        return float(valor_str)
    
    # Cenário 4: Apenas números inteiros sem separadores
    else:
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
    # Melhorada para capturar números com ponto OU vírgula como separador decimal
    # e separadores de milhares opcionais.
    # Pattern para o valor:
    # \d{1,}: Um ou mais dígitos (parte inteira)
    # (?:[.,]\d{3})*: Opcional: um grupo de (ponto ou vírgula seguido por 3 dígitos), repetido zero ou mais vezes (separador de milhar)
    # [.,]\d{2}: Um ponto ou vírgula seguido por exatamente 2 dígitos (parte decimal)
    # OU
    # \d{1,}[.,]\d{2,}: Um ou mais dígitos, seguido por ponto ou vírgula, e 2 ou mais dígitos (para pegar 1,03 ou 1031.87)

    # A regex mais robusta para ambos os casos é pegar qualquer sequência de dígitos, pontos e vírgulas,
    # e deixar a função de conversão fazer o trabalho pesado.
    # Considera:
    # (\d{2}/\d{4})\s+([\d.,]+)
    # ^^^^ Data ^^^^ ^^^^ Valor ^^^^

    # No entanto, para garantir que estamos pegando valores monetários *com* decimais,
    # vamos refinar a parte do valor:
    padrao = r"(\d{2}/\d{4})\s+(\d{1,}(?:[.,]\d{3})*[.,]\d{2})"
    
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
    inputs=[gr.Textbox(label="Cole o texto da CTC aqui. Dúvidas, falar com MarianaP.")],
    outputs=[gr.File(label="Download do arquivo Excel", file_types=[".xlsx"]), gr.Textbox(label="Mensagem")],
)

if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0", server_port=10000) #porta de acesso
