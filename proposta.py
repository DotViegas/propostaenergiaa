import os
import sys
import time
import locale
import logging
import re
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import mm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Configurar logging para o módulo proposta
logger = logging.getLogger(__name__)

######################### RECEBE OS DADOS #########################
nome = "Marcos da Silva Santos Odete"
endereco = "Rua das Flores, 124 - Centro - Campo Grande/MS"
valor_fatura = 439.85
###################################################################

# ===== ENTRADA DE DADOS SIMPLIFICADA =====
# Modifique apenas estes 3 valores:
NOME_COMPLETO = nome
ENDERECO_COMPLETO = endereco
VALOR_FATURA_CLIENTE = str(valor_fatura)  # Formato: XXX.XX (sem R$ e com ponto decimal)

# Configurações fixas
DESCONTO_CONTRATO = 20.0  # 20% de desconto
TARIFA_ENERGISA = 1.138131  # Tarifa da Energisa por kWh

def extrair_valor_monetario(valor_str):
    """Extrai o valor numérico de uma string monetária"""
    # Remove R$, espaços e trabalha com formato XXX.XX
    valor_limpo = re.sub(r'[R$\s]', '', valor_str)
    # Se contém vírgula, converte para ponto
    if ',' in valor_limpo:
        valor_limpo = valor_limpo.replace(',', '.')
    return float(valor_limpo)

def calcular_parametros_automaticos(nome_completo=None, endereco_completo=None, valor_fatura_cliente=None):
    """Calcula automaticamente os parâmetros baseado no valor da fatura do cliente"""
    # Usar valores passados como parâmetro ou valores globais
    nome_usar = nome_completo or NOME_COMPLETO
    endereco_usar = endereco_completo or ENDERECO_COMPLETO
    valor_usar = valor_fatura_cliente or VALOR_FATURA_CLIENTE
    
    valor_fatura = extrair_valor_monetario(valor_usar)
    
    # Definir CONSUMO_MINIMO baseado no valor da fatura
    if valor_fatura <= 300:
        consumo_minimo = 30
    elif valor_fatura <= 500:
        consumo_minimo = 50
    else:
        consumo_minimo = 100
    
    # Calcular o consumo total baseado na fórmula: (valor_fatura - taxa_iluminacao) / tarifa
    # Mas primeiro precisamos descobrir qual seria o consumo ideal
    valor_atualizado_estimado = valor_fatura - (92.51 if valor_fatura > 500 else (61.67 if valor_fatura > 300 else 42.90))
    consumo_estimado = valor_atualizado_estimado / TARIFA_ENERGISA
    
    # Arredondar o consumo para o inteiro mais próximo para ter um valor "limpo"
    consumo_total = round(consumo_estimado)
    
    # Calcular o valor exato do consumo médio baseado no consumo arredondado
    valor_consumo_medio_exato = consumo_total * TARIFA_ENERGISA
    
    # Calcular a taxa de iluminação ajustada para que o total seja exato
    taxa_iluminacao_ajustada = valor_fatura - valor_consumo_medio_exato
    
    return {
        'nome': nome_usar,
        'endereco': endereco_usar,
        'consumo': consumo_total,
        'taxa_iluminacao_publica': taxa_iluminacao_ajustada,
        'consumo_minimo': consumo_minimo,
        'valor_fatura_original': valor_fatura
    }

# Calcular parâmetros automaticamente
parametros = calcular_parametros_automaticos()

# Atribuir aos valores globais para compatibilidade com o resto do código
NOME = parametros['nome']
ENDERECO = parametros['endereco']
CONSUMO = parametros['consumo']
TAXA_ILUMINACAO_PUBLICA = parametros['taxa_iluminacao_publica']
CONSUMO_MINIMO = parametros['consumo_minimo']

# Caminhos dos arquivos
EXPORTADOR_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(EXPORTADOR_DIR, 'fonts')
IMG_DIR = os.path.join(EXPORTADOR_DIR, 'img')
OUTPUT_DIR = os.path.join(EXPORTADOR_DIR, 'media')

def criar_diretorio_saida():
    """Cria o diretório de saída se não existir"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Diretório criado: {OUTPUT_DIR}")

def sanitizar_nome_arquivo(nome):
    """Sanitiza o nome do arquivo removendo caracteres inválidos"""
    # Remove caracteres especiais e substitui por underscore
    nome_sanitizado = re.sub(r'[<>:"/\\|?*]', '_', nome)
    # Remove espaços extras e substitui por underscore
    nome_sanitizado = re.sub(r'\s+', '_', nome_sanitizado.strip())
    # Remove underscores múltiplos
    nome_sanitizado = re.sub(r'_+', '_', nome_sanitizado)
    # Remove underscore no início e fim
    nome_sanitizado = nome_sanitizado.strip('_')
    # Limita o tamanho do nome
    if len(nome_sanitizado) > 50:
        nome_sanitizado = nome_sanitizado[:50]
    return nome_sanitizado

def validar_nome_completo(nome):
    """Valida o campo nome_completo antes da geração do PDF"""
    if not nome or not isinstance(nome, str):
        raise ValueError("Nome completo é obrigatório e deve ser uma string")
    
    nome = nome.strip()
    if len(nome) < 3:
        raise ValueError("Nome completo deve ter pelo menos 3 caracteres")
    
    if len(nome) > 100:
        raise ValueError("Nome completo não pode ter mais de 100 caracteres")
    
    # Verifica se contém pelo menos uma letra
    if not re.search(r'[a-zA-ZÀ-ÿ]', nome):
        raise ValueError("Nome completo deve conter pelo menos uma letra")
    
    return nome

def formatar_moeda(valor):
    """Formata um valor numérico para o formato de moeda brasileiro"""
    try:
        partes = f"{float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.').split(',')
        return f"{partes[0]},{partes[1]}"
    except (ValueError, TypeError):
        return "0,00"

def formatar_inteiro(valor):
    """Formata um número inteiro com separador de milhares"""
    return f"{int(valor):,}".replace(",", ".")

def gerar_grafico(sem_geracao, com_geracao, economia, consumo_minimo_energisa, tax_ilu_pub, desconto):
    """Gera o gráfico de comparação de valores"""
    try:
        # Criar diretório temporário se não existir
        temp_dir = os.path.join(IMG_DIR, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        caminho_imagem = os.path.join(IMG_DIR, 'grafico.png')
        
        plt.style.use('ggplot')
        plt.clf()
        plt.close('all')
        
        # Criar figura
        fig, ax = plt.subplots(figsize=(10, 8.5))
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        
        plt.subplots_adjust(left=0.2)
        
        # Dados para o gráfico
        categorias = ['SEM Geração Solar:', 'COM Geração Solar:']
        
        # Valores para as barras
        concessionaria = [sem_geracao - consumo_minimo_energisa - tax_ilu_pub, 0]
        consumo_minimo_barra = [consumo_minimo_energisa, consumo_minimo_energisa]
        taxa_iluminacao = [tax_ilu_pub, tax_ilu_pub]
        energia_a = [0, com_geracao - consumo_minimo_energisa - tax_ilu_pub]
        
        width = 0.25
        x = np.array([0.3, 0.7])
        
        # Calcular limites do eixo y
        max_value = max(sem_geracao, com_geracao)
        if max_value < 300:
            y_max = np.ceil(max_value / 50) * 50
            y_ticks = np.arange(0, y_max + 50, 50)
        elif max_value < 400:
            y_max = 400
            y_ticks = np.array([0, 66.50, 133.00, 200.50, 267.00, 333.50, 400.00])
        elif max_value < 600:
            y_max = 600
            y_ticks = np.array([0, 100.00, 200.00, 300.00, 400.00, 500.00, 600.00])
        else:
            y_max = np.ceil(max_value / 100) * 100
            intervalo = y_max / 6
            y_ticks = np.array([i * intervalo for i in range(7)])
        
        # Adicionar linhas horizontais
        def add_value_line(y_value):
            ax.hlines(y=y_value, xmin=0, xmax=1.0, 
                     colors='white', linestyles='-', linewidth=1, alpha=1.0,
                     zorder=1)
            ax.text(-0.03, y_value, f"R$ {formatar_moeda(int(y_value))}", 
                   color='white', va='center', ha='right', fontsize=18)
        
        for y_value in y_ticks:
            add_value_line(y_value)
        
        # Função para ajustar altura visual
        def ajustar_altura_visual(valor, valor_maximo):
            if valor == 0:
                return 0
            altura_minima = valor_maximo * 0.05
            if valor < altura_minima:
                return altura_minima
            return valor
        
        # Primeira barra (SEM Geração Solar)
        altura_iluminacao = taxa_iluminacao[0]
        altura_consumo_minimo = consumo_minimo_barra[0]
        
        altura_iluminacao_visual = ajustar_altura_visual(altura_iluminacao, max_value)
        altura_consumo_minimo_visual = ajustar_altura_visual(altura_consumo_minimo, max_value)
        
        ajuste_total = (altura_iluminacao_visual - altura_iluminacao) + (altura_consumo_minimo_visual - altura_consumo_minimo)
        
        altura_concessionaria = sem_geracao - altura_iluminacao - altura_consumo_minimo
        altura_concessionaria_visual = altura_concessionaria - ajuste_total

        # Primeira barra
        ax.bar(x[0], altura_iluminacao_visual, width, 
              label='Iluminação Pública', color='#fc8800', zorder=2)
        ax.bar(x[0], altura_consumo_minimo_visual, width, 
              bottom=altura_iluminacao_visual,
              label='Consumo Mínimo', color='#F4C430', zorder=2)
        ax.bar(x[0], altura_concessionaria_visual, width, 
              bottom=altura_iluminacao_visual + altura_consumo_minimo_visual,
              label='Consumo Compensável', color='#d11d05', zorder=2)
        
        # Segunda barra (COM Geração Solar)
        altura_iluminacao_2 = taxa_iluminacao[1]
        altura_consumo_minimo_2 = consumo_minimo_barra[1]
        
        altura_iluminacao_visual_2 = ajustar_altura_visual(altura_iluminacao_2, max_value)
        altura_consumo_minimo_visual_2 = ajustar_altura_visual(altura_consumo_minimo_2, max_value)
        
        ajuste_total_2 = (altura_iluminacao_visual_2 - altura_iluminacao_2) + (altura_consumo_minimo_visual_2 - altura_consumo_minimo_2)
        
        altura_energia_a = com_geracao - altura_iluminacao_2 - altura_consumo_minimo_2
        altura_energia_a_visual = altura_energia_a - ajuste_total_2

        ax.bar(x[1], altura_iluminacao_visual_2, width,
              color='#fc8800', zorder=2)
        ax.bar(x[1], altura_consumo_minimo_visual_2, width, 
              bottom=altura_iluminacao_visual_2,
              color='#F4C430', zorder=2)
        ax.bar(x[1], altura_energia_a_visual, width, 
              bottom=altura_iluminacao_visual_2 + altura_consumo_minimo_visual_2,
              label='Cons. Comp. c/ Deságio', color='#00b050', zorder=2)

        # Adicionar valores totais abaixo das barras
        def add_total_label(x_pos, total):
            ax.text(x_pos, -y_max*0.07,
                   f"R$ {formatar_moeda(total)}",
                   ha='center', va='top', color='white',
                   fontsize=18)
        
        add_total_label(x[0], sem_geracao)
        add_total_label(x[1], com_geracao)
        
        # Configurações do gráfico
        ax.set_ylim(0, y_max)
        ax.set_xticks(x)
        ax.set_xticklabels(categorias, fontsize=18, color='white')
        ax.set_title('Economia de          na energia solar injetada\n e compensada, ao longo do Contrato.', 
                    color='white', pad=20, fontsize=24)
        
        # Adicionar o valor do desconto
        ax.text(0.375, 1.13, f"{int(desconto)}%", 
                color='white', 
                fontsize=28, 
                ha='center', 
                va='center',
                fontweight='bold',
                transform=ax.transAxes)
        
        # Configurar cores e estilo
        ax.tick_params(colors='white', labelsize=18)
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        
        # Remover bordas
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Remover ticks e labels do eixo y
        ax.tick_params(axis='y', length=0)
        ax.set_yticks([])
        
        # Função para mostrar valores dentro das barras
        def autolabel(rects, valores, offset=0):
            for rect, val in zip(rects, valores):
                if val > 0:
                    height = rect.get_height()
                    # Calcula a posição y no centro da barra atual
                    y_pos = rect.get_y() + height/2
                    
                    # Ajusta o tamanho da fonte para valores grandes
                    font_size = 18
                    if val > 99999:
                        font_size = 16
                    elif val > 9999:
                        font_size = 17
                    
                    ax.text(rect.get_x() + rect.get_width() / 2., y_pos,
                           f"R$ {formatar_moeda(val)}",
                           ha='center', va='center', color='white', 
                           fontsize=font_size, fontweight='bold')
        
        # Adicionar os valores nas barras (usando os valores reais, não os visuais)
        autolabel([ax.patches[0]], [altura_iluminacao])
        autolabel([ax.patches[1]], [altura_consumo_minimo])
        autolabel([ax.patches[2]], [altura_concessionaria])
        
        autolabel([ax.patches[3]], [altura_iluminacao_2])
        autolabel([ax.patches[4]], [altura_consumo_minimo_2])
        autolabel([ax.patches[5]], [altura_energia_a])
        
        # Adicionar legenda
        legend = ax.legend(
            bbox_to_anchor=(0.5, -0.10),  # Posiciona a legenda abaixo do gráfico
            loc='upper center',
            ncol=2,  # Organiza em 2 colunas
            fontsize=14,
            frameon=False,  # Remove a borda da legenda
        )
        
        # Configurar cor do texto da legenda para branco
        for text in legend.get_texts():
            text.set_color('white')

        # Ajustar margens para acomodar a legenda
        plt.subplots_adjust(bottom=0.05)

        # Ajustar layout
        plt.tight_layout()
        
        # Ajustar margens para melhor posicionamento
        plt.subplots_adjust(top=0.831, bottom=0.15)
        
        # Salvar o gráfico
        temp_path = os.path.join(temp_dir, f'grafico_{int(time.time())}.png')
        plt.savefig(temp_path, 
                   transparent=True,
                   bbox_inches='tight',
                   dpi=300,
                   facecolor='none',
                   edgecolor='none')
        plt.close()
        
        # Mover arquivo temporário para destino final
        if os.path.exists(temp_path):
            import shutil
            shutil.move(temp_path, caminho_imagem)
        
        # Limpar arquivos temporários antigos
        for f in os.listdir(temp_dir):
            if f.startswith('grafico_'):
                try:
                    os.remove(os.path.join(temp_dir, f))
                except:
                    pass
        
        print("Gráfico gerado com sucesso")
        return f"{caminho_imagem}?t={int(time.time())}"
        
    except Exception as e:
        print(f"Erro ao gerar gráfico: {str(e)}")
        raise Exception(f"Erro ao gerar gráfico: {str(e)}")

def registrar_fontes():
    """Registra as fontes necessárias para o PDF"""
    try:
        # Verificar se as fontes existem
        fontes = {
            'Calibri-Bold': 'calibrib.ttf',
            'Calibri-Light': 'calibril.ttf',
            'arialmt': 'arialmt.ttf',
            'arialmtbold': 'arialmtbold.ttf'
        }
        
        for nome_fonte, arquivo_fonte in fontes.items():
            caminho_fonte = os.path.join(FONTS_DIR, arquivo_fonte)
            if os.path.exists(caminho_fonte):
                pdfmetrics.registerFont(TTFont(nome_fonte, caminho_fonte))
            else:
                print(f"Aviso: Fonte {arquivo_fonte} não encontrada em {FONTS_DIR}")
        
        return True
    except Exception as e:
        print(f"Erro ao registrar fontes: {str(e)}")
        return False

def calcular_valores_financeiros():
    """Calcula todos os valores financeiros da proposta"""
    # Converter valores para float
    tax_ilu_pub = float(TAXA_ILUMINACAO_PUBLICA)
    cmc_total = float(CONSUMO)
    consumo_minimo = float(CONSUMO_MINIMO)
    desconto = float(DESCONTO_CONTRATO)
    
    # Usar a tarifa já definida globalmente
    tarifa_energisa = TARIFA_ENERGISA
    tarifa_energisa_com_desconto = tarifa_energisa * (1 - desconto / 100)
    tarifa_bandeira_amarela = 0.024181
    tarifa_bandeira_vermelha_patamar_1 = 0.057252 
    tarifa_bandeira_vermelha_patamar_2 = 0.101047 
    tarifa_bandeira_escassez_hibrida = 0.182160 

    # Cálculos financeiros
    energia_energia_a = cmc_total - consumo_minimo
    valor_fatura = tarifa_energisa * cmc_total
    valor_total_fatura = valor_fatura + tax_ilu_pub
    valor_fatura_sem_imposto = tarifa_energisa * energia_energia_a
    fatura_distribuidora = valor_total_fatura - valor_fatura_sem_imposto
    fatura_geradora = tarifa_energisa_com_desconto * energia_energia_a
    total_fatura_energia_a = fatura_distribuidora + fatura_geradora
    energia_compensada = (cmc_total - consumo_minimo) * tarifa_energisa
    consumo_minimo_energisa = consumo_minimo * tarifa_energisa  
    
    # Cálculo do total sem desconto (para o gráfico)
    total_sem_desconto = valor_fatura + tax_ilu_pub
    # Cálculo do valor do desconto
    valor_desconto = total_sem_desconto - total_fatura_energia_a
    total_com_desconto = (valor_fatura - valor_desconto) + tax_ilu_pub

    # Cálculo da fatura com geração solar
    total_fatura_energisa_para_pagar = valor_fatura - energia_compensada
    fatura_locacao = total_fatura_energisa_para_pagar + energia_compensada - valor_desconto
    total_a_pagar_CGS = consumo_minimo_energisa + tax_ilu_pub
    
    # Cálculos de economia
    economia_ano = valor_desconto * 12
    economia_5ano = economia_ano * 5

    economia_incidencia_bandeira_amarela = valor_desconto + energia_energia_a * tarifa_bandeira_amarela
    economia_incidencia_bandeira_vermelha_patamar_1 = valor_desconto + energia_energia_a * tarifa_bandeira_vermelha_patamar_1
    economia_incidencia_bandeira_vermelha_patamar_2 = valor_desconto + energia_energia_a * tarifa_bandeira_vermelha_patamar_2
    economia_incidencia_bandeira_escassez_hibrida = valor_desconto + energia_energia_a * tarifa_bandeira_escassez_hibrida

    economia_anual_incidencia_bandeira_amarela = economia_incidencia_bandeira_amarela * 12
    economia_anual_incidencia_bandeira_vermelha_patamar_1 = economia_incidencia_bandeira_vermelha_patamar_1 * 12
    economia_anual_incidencia_bandeira_vermelha_patamar_2 = economia_incidencia_bandeira_vermelha_patamar_2 * 12
    economia_anual_incidencia_bandeira_escassez_hibrida = economia_incidencia_bandeira_escassez_hibrida * 12

    economia_5ano_incidencia_bandeira_amarela = economia_anual_incidencia_bandeira_amarela * 5
    economia_5ano_incidencia_bandeira_vermelha_patamar_1 = economia_anual_incidencia_bandeira_vermelha_patamar_1 * 5
    economia_5ano_incidencia_bandeira_vermelha_patamar_2 = economia_anual_incidencia_bandeira_vermelha_patamar_2 * 5
    economia_5ano_incidencia_bandeira_escassez_hibrida = economia_anual_incidencia_bandeira_escassez_hibrida * 5
    
    return {
        'tax_ilu_pub': tax_ilu_pub,
        'cmc_total': cmc_total,
        'consumo_minimo': consumo_minimo,
        'desconto': desconto,
        'tarifa_energisa': tarifa_energisa,
        'tarifa_energisa_com_desconto': tarifa_energisa_com_desconto,
        'energia_energia_a': energia_energia_a,
        'valor_fatura': valor_fatura,
        'valor_total_fatura': valor_total_fatura,
        'valor_fatura_sem_imposto': valor_fatura_sem_imposto,
        'fatura_distribuidora': fatura_distribuidora,
        'fatura_geradora': fatura_geradora,
        'total_fatura_energia_a': total_fatura_energia_a,
        'energia_compensada': energia_compensada,
        'consumo_minimo_energisa': consumo_minimo_energisa,
        'total_sem_desconto': total_sem_desconto,
        'valor_desconto': valor_desconto,
        'total_com_desconto': total_com_desconto,
        'total_fatura_energisa_para_pagar': total_fatura_energisa_para_pagar,
        'fatura_locacao': fatura_locacao,
        'total_a_pagar_CGS': total_a_pagar_CGS,
        'economia_ano': economia_ano,
        'economia_5ano': economia_5ano,
        'economia_incidencia_bandeira_amarela': economia_incidencia_bandeira_amarela,
        'economia_incidencia_bandeira_vermelha_patamar_1': economia_incidencia_bandeira_vermelha_patamar_1,
        'economia_incidencia_bandeira_vermelha_patamar_2': economia_incidencia_bandeira_vermelha_patamar_2,
        'economia_incidencia_bandeira_escassez_hibrida': economia_incidencia_bandeira_escassez_hibrida,
        'economia_anual_incidencia_bandeira_amarela': economia_anual_incidencia_bandeira_amarela,
        'economia_anual_incidencia_bandeira_vermelha_patamar_1': economia_anual_incidencia_bandeira_vermelha_patamar_1,
        'economia_anual_incidencia_bandeira_vermelha_patamar_2': economia_anual_incidencia_bandeira_vermelha_patamar_2,
        'economia_anual_incidencia_bandeira_escassez_hibrida': economia_anual_incidencia_bandeira_escassez_hibrida,
        'economia_5ano_incidencia_bandeira_amarela': economia_5ano_incidencia_bandeira_amarela,
        'economia_5ano_incidencia_bandeira_vermelha_patamar_1': economia_5ano_incidencia_bandeira_vermelha_patamar_1,
        'economia_5ano_incidencia_bandeira_vermelha_patamar_2': economia_5ano_incidencia_bandeira_vermelha_patamar_2,
        'economia_5ano_incidencia_bandeira_escassez_hibrida': economia_5ano_incidencia_bandeira_escassez_hibrida
    }

def criar_proposta_pdf():
    """Cria o PDF da proposta"""
    try:
        # Validar nome completo antes da geração
        nome_validado = validar_nome_completo(NOME)
        logger.info(f"Iniciando geração de PDF para: {nome_validado}")
        
        # Calcular valores financeiros
        valores = calcular_valores_financeiros()
        
        # Gerar gráfico
        print("Gerando gráfico...")
        if not gerar_grafico(
            valores['total_sem_desconto'],
            valores['total_fatura_energia_a'],
            valores['valor_desconto'],
            valores['consumo_minimo_energisa'],
            valores['tax_ilu_pub'],
            valores['desconto']
        ):
            print("Erro ao gerar gráfico, continuando sem ele...")
        
        # Registrar fontes
        if not registrar_fontes():
            print("Erro ao registrar fontes, usando fontes padrão...")
        
        # Configurar locale para data
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
            except locale.Error:
                pass
        
        # Data atual
        data_atual_obj = datetime.now()
        mes_hoje = data_atual_obj.strftime("%B").upper()
        ano_hoje = data_atual_obj.strftime("%Y")
        
        # Mapeamento de meses em português
        meses_dict = {
            'JANUARY': 'JANEIRO', 'FEBRUARY': 'FEVEREIRO', 'MARCH': 'MARÇO',
            'APRIL': 'ABRIL', 'MAY': 'MAIO', 'JUNE': 'JUNHO',
            'JULY': 'JULHO', 'AUGUST': 'AGOSTO', 'SEPTEMBER': 'SETEMBRO',
            'OCTOBER': 'OUTUBRO', 'NOVEMBER': 'NOVEMBRO', 'DECEMBER': 'DEZEMBRO'
        }
        mes_hoje = meses_dict.get(mes_hoje, mes_hoje)
        mes_extenso = f"{mes_hoje}/{ano_hoje}"

        # Formatação dos valores
        valor_fatura_fmt = formatar_moeda(valores['valor_fatura'])
        desconto_fmt = int(valores['desconto'])
        tax_ilu_pub_fmt = formatar_moeda(valores['tax_ilu_pub'])
        valor_total_fatura_fmt = formatar_moeda(valores['valor_total_fatura'])
        valor_desconto_fmt = formatar_moeda(valores['valor_desconto'])
        total_fatura_energia_a_fmt = formatar_moeda(valores['total_fatura_energia_a'])
        economia_ano_fmt = formatar_moeda(valores['economia_ano'])
        economia_5ano_fmt = formatar_moeda(valores['economia_5ano'])
        tarifa_energisa_fmt = f"{valores['tarifa_energisa']:.6f}".replace('.', ',')
        tarifa_energisa_com_desconto_fmt = f"{valores['tarifa_energisa_com_desconto']:.6f}".replace('.', ',')
        cmc_total_fmt = int(valores['cmc_total'])
        energia_energia_a_fmt = int(valores['energia_energia_a'])
        valor_fatura_sem_imposto_fmt = formatar_moeda(valores['valor_fatura_sem_imposto'])
        consumo_minimo_fmt = int(valores['consumo_minimo'])
        total_a_pagar_CGS_fmt = formatar_moeda(valores['total_a_pagar_CGS'])
        fatura_geradora_fmt = formatar_moeda(valores['fatura_geradora'])
        
        # Formatação das economias com bandeiras
        economia_incidencia_bandeira_amarela_fmt = formatar_moeda(valores['economia_incidencia_bandeira_amarela'])
        economia_incidencia_bandeira_vermelha_patamar_1_fmt = formatar_moeda(valores['economia_incidencia_bandeira_vermelha_patamar_1'])
        economia_incidencia_bandeira_vermelha_patamar_2_fmt = formatar_moeda(valores['economia_incidencia_bandeira_vermelha_patamar_2'])
        economia_incidencia_bandeira_escassez_hibrida_fmt = formatar_moeda(valores['economia_incidencia_bandeira_escassez_hibrida'])
        economia_anual_incidencia_bandeira_amarela_fmt = formatar_moeda(valores['economia_anual_incidencia_bandeira_amarela'])
        economia_anual_incidencia_bandeira_vermelha_patamar_1_fmt = formatar_moeda(valores['economia_anual_incidencia_bandeira_vermelha_patamar_1'])
        economia_anual_incidencia_bandeira_vermelha_patamar_2_fmt = formatar_moeda(valores['economia_anual_incidencia_bandeira_vermelha_patamar_2'])
        economia_anual_incidencia_bandeira_escassez_hibrida_fmt = formatar_moeda(valores['economia_anual_incidencia_bandeira_escassez_hibrida'])
        economia_5ano_incidencia_bandeira_amarela_fmt = formatar_moeda(valores['economia_5ano_incidencia_bandeira_amarela'])
        economia_5ano_incidencia_bandeira_vermelha_patamar_1_fmt = formatar_moeda(valores['economia_5ano_incidencia_bandeira_vermelha_patamar_1'])
        economia_5ano_incidencia_bandeira_vermelha_patamar_2_fmt = formatar_moeda(valores['economia_5ano_incidencia_bandeira_vermelha_patamar_2'])
        economia_5ano_incidencia_bandeira_escassez_hibrida_fmt = formatar_moeda(valores['economia_5ano_incidencia_bandeira_escassez_hibrida'])

        # Criar arquivo PDF
        nome_sanitizado = sanitizar_nome_arquivo(NOME)
        nome_arquivo = f"simulacao_{nome_sanitizado}.pdf"
        caminho_arquivo = os.path.join(OUTPUT_DIR, nome_arquivo)
        
        # Create PDF file
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        largura, altura = A4

        # Função para desenhar gradiente
        def desenhar_gradiente(canvas, x, y, largura, altura, cor1, cor2):
            def hex_para_rgb(hex_color):
                hex_color = hex_color.lstrip("#")
                return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))

            rgb1 = hex_para_rgb(cor1)
            rgb2 = hex_para_rgb(cor2)

            steps = 300
            for i in range(steps):
                t = i / steps
                r = rgb1[0] * (1 - t) + rgb2[0] * t
                g = rgb1[1] * (1 - t) + rgb2[1] * t
                b = rgb1[2] * (1 - t) + rgb2[2] * t
                canvas.setFillColorRGB(r, g, b)
                canvas.rect(x - 2 + largura * (1 - t), y - 2, largura / steps + 4, altura + 4, stroke=0, fill=1)

        # Desenhar gradiente de fundo
        desenhar_gradiente(p, 0, 0, largura, altura, "#0b4882", "#0c243c")

        # Adicionar a imagem modelo se existir
        modelo_path = os.path.join(IMG_DIR, 'modelo-SEM-texto.png')
        if os.path.exists(modelo_path):
            p.drawImage(
                modelo_path,
                0, 0, largura, altura,
                mask='auto',
                preserveAspectRatio=True
            )

        # Criar tabela com nome e endereço
        nome_maiusculo = NOME.upper()
        end_com = ENDERECO

        # Definir largura da tabela
        tabela_largura = largura * 0.4
        
        # Criar estilos
        estilo_nome = ParagraphStyle(
            'NomeStyle',
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=colors.white,
            leading=15,
            spaceBefore=0,
            spaceAfter=0,
            alignment=TA_CENTER,
            wordWrap='LongWords'
        )
        
        estilo_endereco = ParagraphStyle(
            'EnderecoStyle',
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=colors.white,
            leading=12,
            spaceBefore=0,
            spaceAfter=0,
            alignment=TA_CENTER,
            wordWrap='LongWords'
        )
        
        # Criar dados da tabela
        dados = [
            [Paragraph(nome_maiusculo, estilo_nome)],
            [Paragraph(end_com, estilo_endereco)]
        ]
        
        # Criar a tabela
        table = Table(
            dados, 
            colWidths=[tabela_largura],
            rowHeights=None
        )
        
        # Estilo da tabela
        style = TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ])
        
        table.setStyle(style)
        
        # Posicionar a tabela
        table_x = largura * 0.55
        table_y = altura - 40
        
        # Desenhar a tabela
        w, h = table.wrapOn(p, largura, altura)
        table.drawOn(p, table_x, table_y - h)

        # Adicionar borda arredondada ao redor do gráfico
        p.setStrokeColorRGB(1, 1, 1)
        p.setLineWidth(0.5)
        p.roundRect(45, altura - 427, 230, 195, 15)

        # Adicionar imagem do gráfico se existir (posição corrigida)
        grafico_path = os.path.join(IMG_DIR, 'grafico.png')
        if os.path.exists(grafico_path):
            p.drawImage(grafico_path, 48, altura - 425, width=225, height=190, preserveAspectRatio=True, mask="auto")

        # Adicionar texto de economia
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Helvetica-Bold", 18)
        p.drawCentredString(155, altura - 195, "Economia")
                            
        p.setFont("Helvetica-Bold", 12)
        p.drawCentredString(70, altura - 213, "Mensal")
        p.drawCentredString(150, altura - 213, "Anual")
        p.drawCentredString(240, altura - 213, "Em 5 anos")

        # Ajustar tamanho da fonte para valores mensais maiores que 9.999
        if valores['valor_desconto'] > 9999:
            p.setFont("Helvetica-Bold", 12)
        else:
            p.setFont("Helvetica-Bold", 14)
            
        p.drawCentredString(70, altura - 227, f"R${valor_desconto_fmt}")
        p.drawCentredString(150, altura - 227, f"R${economia_ano_fmt}")
        p.drawCentredString(240, altura - 227, f"R${economia_5ano_fmt}")

        # Seção da fatura SEM geração solar
        p.setFillColorRGB(0, 0, 0)
        p.setFont("arialmtbold", 8)
        p.drawCentredString(425, altura - 199, "(Antes) Fatura Distribuidora SEM GERAÇÃO SOLAR")

        # Cabeçalho da primeira tabela
        p.setFont("arialmtbold", 4)
        p.drawString(306, altura - 222, "Itens da Fatura")
        p.drawString(430, altura - 222, "Unid")
        p.drawRightString(470, altura - 222, "Quant")
        p.drawString(482, altura - 217, "Preço Unit")
        p.drawString(482, altura - 222, "C/ Tributos (R$)*")
        p.drawRightString(542, altura - 222, "Valor (R$)")

        # Linha horizontal
        p.setStrokeColorRGB(0, 0, 0)
        p.setLineWidth(0.5)
        p.line(306, altura - 224, 542, altura - 224)

        # Dados da fatura sem geração
        p.setFont("arialmt", 4)
        p.drawString(307, altura - 229, "Consumo Médio Mensal")
        p.drawString(430, altura - 229, "KWH")
        p.drawRightString(470, altura - 229, f"{cmc_total_fmt}")
        p.drawRightString(514, altura - 229, f"R$ {tarifa_energisa_fmt}")
        p.drawRightString(542, altura - 229, f"R$ {valor_fatura_fmt}")

        p.drawString(307, altura - 235, "LANÇAMENTOS E SERVIÇOS")
        p.drawString(430, altura - 235, " ")
        p.drawRightString(470, altura - 235, f" ")
        p.drawRightString(514, altura - 235, f" ")
        p.drawRightString(542, altura - 235, f" ")

        p.drawString(307, altura - 241, "CONTRIBUIÇÃO ILUMINAÇÃO PÚBLICA (CIP)")
        p.drawRightString(542, altura - 241, f"R$ {tax_ilu_pub_fmt}")

        # Total da primeira fatura
        p.setFont("arialmtbold", 6)
        p.drawRightString(504, altura - 260, f"TOTAL A PAGAR")
        p.drawRightString(542, altura - 260, f"R$ {valor_total_fatura_fmt}")

        # Nota sobre tarifas
        p.setFont("arialmt", 4)
        p.drawString(307, altura - 273, f"*Tarifas e tributos praticados pela Distribuidora em {mes_extenso} de {ano_hoje}")

        # Seção da fatura COM geração solar
        p.setFillColorRGB(0, 0, 0)
        p.setFont("arialmtbold", 8)
        p.drawCentredString(425, altura - 289, "(Depois) Fatura Distribuidora COM GERAÇÃO SOLAR")

        # Cabeçalho da segunda tabela
        p.setFont("arialmtbold", 4)
        p.drawString(306, altura - 307, "Itens da Fatura")
        p.drawString(430, altura - 307, "Unid")
        p.drawRightString(470, altura - 307, "Quant")
        p.drawString(485, altura - 307, "Preço Unit (R$)")
        p.drawRightString(542, altura - 307, "Valor (R$)")

        # Linha horizontal
        p.setStrokeColorRGB(0, 0, 0)
        p.setLineWidth(0.5)
        p.line(306, altura - 309, 542, altura - 309)

        # Dados da fatura com geração
        p.setFont("arialmt", 4)
        p.drawString(307, altura - 314, "Consumo Médio Mensal")
        p.drawString(430, altura - 314, "KWH")
        p.drawRightString(470, altura - 314, f"{cmc_total_fmt}")
        p.drawRightString(514, altura - 314, f"R$ {tarifa_energisa_fmt}")
        p.drawRightString(542, altura - 314, f"R$ {valor_fatura_fmt}")

        p.drawString(307, altura - 320, "Energia Solar")
        p.drawString(430, altura - 320, "KWH")
        p.drawRightString(470, altura - 320, f"{energia_energia_a_fmt}")
        p.drawRightString(514, altura - 320, f"R$ {tarifa_energisa_fmt}")
        # Valor em vermelho (negativo)
        p.setStrokeColorRGB(1, 0, 0)
        p.setFillColorRGB(1, 0, 0)
        p.setFont("arialmtbold", 4)
        p.drawRightString(542, altura - 320, f"-R$ {valor_fatura_sem_imposto_fmt}")

        # Volta para cor preta
        p.setStrokeColorRGB(0, 0, 0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("arialmt", 4)
        p.drawString(307, altura - 326, "CONTRIBUIÇÃO ILUMINAÇÃO PÚBLICA (CIP)")
        p.drawRightString(542, altura - 326, f"R$ {tax_ilu_pub_fmt}")

        # Valor fixo residual
        p.setFont("arialmtbold", 6)
        p.drawRightString(504, altura - 339, f"VALOR FIXO RESIDUAL**")
        p.drawRightString(542, altura - 339, f"R$ {total_a_pagar_CGS_fmt}")

        # Explicação do valor residual
        p.setFont("arialmt", 4)
        p.drawString(307, altura - 351, f"**O valor residual é resultado da cobrança obrigatória do Custo de Disponibilidade ({consumo_minimo_fmt}kWh) + CIP")

        # Seção "O que vou pagar"
        p.setFillColorRGB(0, 0, 0)
        p.setFont("arialmtbold", 8)
        p.drawCentredString(425, altura - 365, "O que vou pagar:")

        # Cabeçalho da terceira tabela
        p.setFont("arialmtbold", 4)
        p.drawString(306, altura - 380, "Itens da Fatura")
        p.drawString(430, altura - 380, "Unid")
        p.drawRightString(470, altura - 380, "Quant")
        p.drawString(485, altura - 380, "Preço Unit (R$)")
        p.drawRightString(542, altura - 380, "Valor (R$)")

        # Linha horizontal
        p.setStrokeColorRGB(0, 0, 0)
        p.setLineWidth(0.5)
        p.line(306, altura - 382, 542, altura - 382)

        # Dados do que vai pagar
        p.setFont("arialmt", 4)
        p.drawString(307, altura - 387, f"VALOR DE LOCAÇÃO**** (Geração Solar c/ {desconto_fmt}% de deságio)")
        p.drawString(430, altura - 387, "KWH")
        p.drawRightString(470, altura - 387, f"{energia_energia_a_fmt}")
        p.drawRightString(514, altura - 387, f"R$ {tarifa_energisa_com_desconto_fmt}")
        p.drawRightString(542, altura - 387, f"R$ {fatura_geradora_fmt}")

        p.drawString(307, altura - 393, f"VALOR FIXO RESIDUAL DISTRIBUIDORA (Consumo Mínimo de {consumo_minimo_fmt}kWh + CIP)")
        p.drawRightString(542, altura - 393, f"R$ {total_a_pagar_CGS_fmt}")

        # Total da fatura com geração
        p.setFont("arialmtbold", 6)
        p.drawRightString(504, altura - 405, f"VALOR TOTAL DA FATURA COM GERAÇÃO SOLAR")
        p.drawRightString(542, altura - 405, f"R$ {total_fatura_energia_a_fmt}")

        # Notas explicativas
        p.setFont("arialmt", 4)
        p.drawString(307, altura - 417, f"***Não pagar a fatura residual da Distribuidora. Pagar somente a Fatura LOCAÇÃO.")
        p.drawString(307, altura - 423, f"****O valor estimado com base na performance de geração de creditos a compensar no ciclo de faturamento.")

        # Seção Imobiliária Solar
        p.setFillColorRGB(1, 1, 1)  # Branco
        p.setFont("Calibri-Light", 14)
        p.drawString(35, altura - 533, f"A")
        p.setFillColorRGB(255/255, 194/255, 14/255)  # Amarelo
        p.setFont("Calibri-Bold", 14)
        p.drawString(47, altura - 533, f"Energia Solar por Assinatura")
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Calibri-Light", 14)
        p.drawString(211, altura - 533, f" é um modelo de negócio que permite às pessoas físicas e")
        p.drawString(35, altura - 546, f"jurídicas gerarem sua própria energia solar e se beneficiar do sistema de compensação da")
        p.drawString(35, altura - 559, f"Distribuidora sem a necessidade de realizar obras ou investimentos, sem taxas, sem fidelização")
        p.drawString(35, altura - 572, f"e sem gastos com manutenção. Na prática, você loca uma parcela da usina solar já em operação.")

        # Título "Passos"
        p.setFillColorRGB(255/255, 194/255, 14/255)
        p.setFont("Calibri-Bold", 11)
        p.drawString(190, 245, f"Passos")

        # Passos do processo
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Calibri-Light", 9)
        p.drawString(110, 235, f"1º) Você nos encaminha sua(s) conta(s) de luz. Analisamos")
        p.drawString(110, 226, f"o seu consumo, estimamos sua economia e lhe apresentamos")
        p.drawString(110, 217, f"nosso")
        p.setFillColorRGB(255/255, 194/255, 14/255)
        p.setFont("Calibri-Bold", 9)
        p.drawString(133, 217, f"Estudo-Proposta")
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Calibri-Light", 9)
        p.drawString(193, 217, f".")

        p.drawString(110, 200, f"2º) Você aprova a proposta e nos envia os seguintes")
        p.drawString(110, 192, f"documentos:")
        p.drawString(110, 184, f" -  Cópia do documento pessoal do titular da conta de luz;")
        p.drawString(110, 176, f" -  Se Pessoa Jurídica: i) cópia do Contrato Social e ii) cópia do")
        p.drawString(110, 168, f"    cartão CNPJ.")

        p.drawString(110, 149, f"3º) Você receberá o contrato por e-mail e")
        p.setFillColorRGB(255/255, 194/255, 14/255)
        p.setFont("Calibri-Bold", 9)
        p.drawString(262, 149, f"assinará digitalmente")
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Calibri-Light", 9)
        p.drawString(339, 149, f".")

        p.drawString(110, 122, f"4º) Assumiremos a titularidade da(s) sua(s) unidade(s)")
        p.drawString(110, 114, f"consumidora(s) beneficiárias e cuidaremos de toda a")
        p.setFillColorRGB(255/255, 194/255, 14/255)
        p.setFont("Calibri-Bold", 9)
        p.drawString(110, 106, f"Comunicação com a Distribuidora")
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Calibri-Light", 9)
        p.drawString(235, 106, f"para garantir sua")
        p.drawString(110, 98, f"economia sem complicações")

        p.drawString(110, 71, f"5º) Em até 90 dias você passa a")
        p.setFillColorRGB(255/255, 194/255, 14/255)
        p.setFont("Calibri-Bold", 9)
        p.drawString(225, 71, f"usufruir de energia limpa,")
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Calibri-Light", 9)
        p.drawString(110, 63, f"renovável e mais barata.")

        p.drawString(110, 40, f"6) Você contará com 100% do nosso")
        p.setFillColorRGB(255/255, 194/255, 14/255)
        p.setFont("Calibri-Bold", 9)
        p.drawString(243, 40, f"suporte técnico e")
        p.drawString(110, 32, f"comercial vitalício")
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Calibri-Light", 9)
        p.drawString(177, 32, f"(durante toda a vigência do seu contrato")
        p.drawString(110, 24, f"conosco), através do nosso WhatsApp (67) 9 9343-1808.")

        # Salvar o PDF
        p.save()
        
        # Escrever o buffer para arquivo
        with open(caminho_arquivo, 'wb') as f:
            f.write(buffer.getvalue())
        
        # Log de sucesso com informações detalhadas
        logger.info(f"PDF gerado com sucesso!")
        logger.info(f"Arquivo: {nome_arquivo}")
        logger.info(f"Caminho completo: {caminho_arquivo}")
        logger.info(f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        return caminho_arquivo
        
    except Exception as e:
        # Log de falha com detalhes do erro
        logger.error(f"Falha na geração do PDF!")
        logger.error(f"Erro: {str(e)}")
        logger.error(f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        return None

def processar_proposta_webhook(nome_completo, endereco, valor_fatura):
    """
    Função principal para processar dados do webhook e gerar proposta PDF
    
    Args:
        nome_completo (str): Nome completo do cliente
        endereco (str): Endereço completo do cliente  
        valor_fatura (str): Valor da fatura de energia
        
    Returns:
        dict: Resultado do processamento com sucesso/erro e caminho do arquivo
    """
    try:
        logger.info(f"Iniciando processamento da proposta para {nome_completo}")
        
        # Validar dados de entrada
        if not nome_completo or len(nome_completo.strip()) < 3:
            raise ValueError("Nome completo deve ter pelo menos 3 caracteres")
        
        if not endereco or len(endereco.strip()) < 10:
            raise ValueError("Endereço deve ter pelo menos 10 caracteres")
        
        if not valor_fatura:
            raise ValueError("Valor da fatura é obrigatório")
        
        # Validar valor da fatura
        try:
            valor_float = float(valor_fatura)
            if valor_float <= 0:
                raise ValueError("Valor da fatura deve ser maior que zero")
        except ValueError:
            raise ValueError("Valor da fatura deve ser um número válido")
        
        # Calcular parâmetros com os dados do webhook
        parametros_webhook = calcular_parametros_automaticos(
            nome_completo=nome_completo.strip(),
            endereco_completo=endereco.strip(),
            valor_fatura_cliente=valor_fatura
        )
        
        # Atualizar variáveis globais temporariamente para gerar o PDF
        global NOME, ENDERECO, CONSUMO, TAXA_ILUMINACAO_PUBLICA, CONSUMO_MINIMO
        
        # Salvar valores originais
        nome_original = NOME
        endereco_original = ENDERECO
        consumo_original = CONSUMO
        taxa_original = TAXA_ILUMINACAO_PUBLICA
        consumo_minimo_original = CONSUMO_MINIMO
        
        try:
            # Atualizar com valores do webhook
            NOME = parametros_webhook['nome']
            ENDERECO = parametros_webhook['endereco']
            CONSUMO = parametros_webhook['consumo']
            TAXA_ILUMINACAO_PUBLICA = parametros_webhook['taxa_iluminacao_publica']
            CONSUMO_MINIMO = parametros_webhook['consumo_minimo']
            
            # Criar diretório de saída se não existir
            criar_diretorio_saida()
            
            # Gerar o PDF
            arquivo_path = criar_proposta_pdf()
            
            if not arquivo_path:
                raise Exception("Falha na criação do arquivo PDF")
            
            if not os.path.exists(arquivo_path):
                raise Exception("Arquivo PDF não foi criado corretamente")
            
            logger.info(f"Proposta gerada com sucesso: {arquivo_path}")
            
            return {
                'sucesso': True,
                'arquivo_path': arquivo_path,
                'dados_processados': parametros_webhook,
                'message': 'Proposta gerada com sucesso'
            }
            
        finally:
            # Restaurar valores originais
            NOME = nome_original
            ENDERECO = endereco_original
            CONSUMO = consumo_original
            TAXA_ILUMINACAO_PUBLICA = taxa_original
            CONSUMO_MINIMO = consumo_minimo_original
            
    except Exception as e:
        error_msg = f"Erro ao processar proposta: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'sucesso': False,
            'erro': error_msg,
            'arquivo_path': None
        }

def main():
    """Função principal"""
    print("=== EXPORTADOR DE PROPOSTAS ===")
    print("=== ENTRADA DE DADOS ===")
    print(f"Nome Completo: {NOME_COMPLETO}")
    print(f"Endereço Completo: {ENDERECO_COMPLETO}")
    print(f"Valor da Fatura Cliente: {VALOR_FATURA_CLIENTE}")
    print()
    print("=== VALORES CALCULADOS AUTOMATICAMENTE ===")
    print(f"Consumo Total: {CONSUMO} kWh")
    print(f"Taxa de Iluminação Pública: R$ {TAXA_ILUMINACAO_PUBLICA}")
    print(f"Consumo Mínimo: {CONSUMO_MINIMO} kWh")
    print(f"Desconto do Contrato: {DESCONTO_CONTRATO}%")
    print(f"Valor Original da Fatura: R$ {parametros['valor_fatura_original']:.2f}")
    print()
    
    # Criar diretório de saída
    criar_diretorio_saida()
    
    # Criar proposta
    arquivo_criado = criar_proposta_pdf()
    
    if arquivo_criado:
        print(f"\n✅ Proposta salva em: {arquivo_criado}")
    else:
        print("\n❌ Erro ao criar proposta")

if __name__ == "__main__":
    main()