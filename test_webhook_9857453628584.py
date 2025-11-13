"""
Script de teste para requisição de proposta/simulação
Testa o endpoint /webhook_proposta
"""

import requests
import json

# URL do endpoint
# Usar localhost no Windows ao invés de 0.0.0.0
URL = "http://localhost:8000/webhook_proposta"

# Dados de teste
# Versão 1: Com endereço
dados_teste_completo = {
    "nome_completo": "João da Silva Santos",
    "endereco": "Rua das Palmeiras, 456 - Centro - Campo Grande/MS",
    "valor_fatura": "550.75"
}

# Versão 2: Sem endereço (se não for obrigatório)
dados_teste_sem_endereco = {
    "nome_completo": "João da Silva Santos",
    "valor_fatura": "550.75"
}

# Escolha qual usar (altere aqui)
dados_teste = dados_teste_completo  # Com endereço (obrigatório)

def testar_requisicao():
    """Testa a requisição para o endpoint de proposta"""
    print("=" * 60)
    print("TESTE DE REQUISIÇÃO - WEBHOOK PROPOSTA")
    print("=" * 60)
    print(f"\nURL: {URL}")
    print(f"\nDados enviados:")
    print(json.dumps(dados_teste, indent=2, ensure_ascii=False))
    print("\n" + "-" * 60)
    
    try:
        # Fazer a requisição POST
        print("\nEnviando requisição...")
        response = requests.post(URL, json=dados_teste, timeout=30)
        
        # Exibir status code
        print(f"\nStatus Code: {response.status_code}")
        
        # Exibir resposta
        print("\nResposta do servidor:")
        print("-" * 60)
        
        if response.status_code == 200:
            resposta_json = response.json()
            print(json.dumps(resposta_json, indent=2, ensure_ascii=False))
            
            # Exibir informações importantes
            print("\n" + "=" * 60)
            print("RESUMO DA PROPOSTA GERADA")
            print("=" * 60)
            print(f"Status: {resposta_json.get('status')}")
            print(f"Arquivo: {resposta_json.get('arquivo_nome')}")
            print(f"URL do arquivo: {resposta_json.get('arquivo_url')}")
            print(f"Valor desconto: R$ {resposta_json.get('valor_desconto')}")
            print(f"Economia anual: R$ {resposta_json.get('economia_ano')}")
            print(f"Economia 5 anos: R$ {resposta_json.get('economia_5ano')}")
            print("=" * 60)
            
        else:
            print(f"Erro: {response.text}")
            try:
                erro_json = response.json()
                print("\nDetalhes do erro:")
                print(json.dumps(erro_json, indent=2, ensure_ascii=False))
            except:
                pass
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERRO: Não foi possível conectar ao servidor.")
        print("Verifique se o servidor está rodando em http://0.0.0.0:8000")
        print("\nPara iniciar o servidor, execute:")
        print("  python app.py")
        
    except requests.exceptions.Timeout:
        print("\n❌ ERRO: Timeout na requisição (mais de 30 segundos)")
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")

def testar_validacoes():
    """Testa as validações do endpoint"""
    print("\n\n" + "=" * 60)
    print("TESTE DE VALIDAÇÕES")
    print("=" * 60)
    
    testes_validacao = [
        {
            "nome": "Nome muito curto",
            "dados": {
                "nome_completo": "Jo",
                "endereco": "Rua das Flores, 123",
                "valor_fatura": "100.00"
            }
        },
        {
            "nome": "Endereço muito curto",
            "dados": {
                "nome_completo": "João Silva",
                "endereco": "Rua 1",
                "valor_fatura": "100.00"
            }
        },
        {
            "nome": "Valor fatura inválido",
            "dados": {
                "nome_completo": "João Silva",
                "endereco": "Rua das Flores, 123",
                "valor_fatura": "abc"
            }
        }
    ]
    
    for teste in testes_validacao:
        print(f"\n{teste['nome']}:")
        print(f"Dados: {teste['dados']}")
        
        try:
            response = requests.post(URL, json=teste['dados'], timeout=10)
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Resposta: {response.json()}")
        except Exception as e:
            print(f"Erro: {str(e)}")

if __name__ == "__main__":
    # Teste principal
    testar_requisicao()
    
    # Descomentar para testar validações
    # testar_validacoes()
