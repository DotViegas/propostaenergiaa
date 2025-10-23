import os
import base64
import uuid
import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from proposta import processar_proposta_webhook

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webhook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurar rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Proposta FastAPI", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Modelo Pydantic para validação dos dados do webhook
class WebhookData(BaseModel):
    nome_completo: str
    endereco: str
    valor_fatura: str
    
    @validator('nome_completo')
    def validate_nome_completo(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Nome completo deve ter pelo menos 3 caracteres')
        return v.strip()
    
    @validator('endereco')
    def validate_endereco(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('Endereço deve ter pelo menos 10 caracteres')
        return v.strip()
    
    @validator('valor_fatura')
    def validate_valor_fatura(cls, v):
        if not v:
            raise ValueError('Valor da fatura é obrigatório')
        
        # Remover caracteres não numéricos exceto vírgula e ponto
        valor_limpo = ''.join(c for c in v if c.isdigit() or c in '.,')
        
        if not valor_limpo:
            raise ValueError('Valor da fatura deve conter números')
        
        # Converter vírgula para ponto se necessário
        if ',' in valor_limpo:
            valor_limpo = valor_limpo.replace(',', '.')
        
        try:
            valor_float = float(valor_limpo)
            if valor_float <= 0:
                raise ValueError('Valor da fatura deve ser maior que zero')
            if valor_float > 99999.99:
                raise ValueError('Valor da fatura muito alto')
            return str(valor_float)
        except ValueError:
            raise ValueError('Valor da fatura deve ser um número válido')

@app.get("/")
async def root():
    return {"status": 200, "message": "Proposta FastAPI - Sistema de Webhook para Geração de Propostas", "version": "1.0.0", "proprietario": "Energia A", "contato admin": "viegas@energiaa.com.br"}

@app.post("/webhook_proposta")
@limiter.limit("10/minute")  # Limite de 10 requisições por minuto por IP
async def webhook_proposta(request: Request, data: WebhookData):
    """
    Endpoint webhook para processar dados e gerar proposta PDF
    
    Recebe dados do cliente, valida, processa através do script proposta.py
    e retorna informações do arquivo gerado.
    """
    try:
        # Log da requisição recebida
        client_ip = get_remote_address(request)
        logger.info(f"Webhook recebido de {client_ip} - Nome: {data.nome_completo}")
        
        # Verificar se a pasta media existe, criar se necessário
        media_dir = os.path.join(os.path.dirname(__file__), 'media')
        if not os.path.exists(media_dir):
            os.makedirs(media_dir)
            logger.info(f"Diretório media criado: {media_dir}")
        
        # Processar dados através do proposta.py
        resultado = processar_proposta_webhook(
            nome_completo=data.nome_completo,
            endereco=data.endereco,
            valor_fatura=data.valor_fatura
        )
        
        if not resultado['sucesso']:
            logger.error(f"Erro no processamento: {resultado['erro']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro no processamento: {resultado['erro']}"
            )
        
        # Ler o arquivo gerado e converter para base64
        arquivo_path = resultado['arquivo_path']
        
        if not os.path.exists(arquivo_path):
            logger.error(f"Arquivo não encontrado: {arquivo_path}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Arquivo gerado não encontrado"
            )
        
        # Copiar arquivo para pasta media com nome único
        nome_arquivo_media = f"proposta_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        arquivo_media_path = os.path.join(media_dir, nome_arquivo_media)
        
        # Copiar arquivo
        import shutil
        shutil.copy2(arquivo_path, arquivo_media_path)
        
        # Ler arquivo e converter para base64
        with open(arquivo_media_path, 'rb') as f:
            arquivo_bytes = f.read()
            arquivo_base64 = base64.b64encode(arquivo_bytes).decode('utf-8')
        
        # Construir URL completa do arquivo
        # Nota: Em produção, você deve configurar o domínio correto
        base_url = str(request.base_url).rstrip('/')
        arquivo_url = f"{base_url}/media/{nome_arquivo_media}"
        
        # Log de sucesso
        logger.info(f"Proposta gerada com sucesso: {nome_arquivo_media}")
        
        # Retornar resposta
        return {
            "status": "sucesso",
            "message": "Proposta gerada com sucesso",
            "arquivo_url": arquivo_url,
            "arquivo_nome": nome_arquivo_media,
            "arquivo_base64": arquivo_base64,
            "dados_processados": {
                "nome_completo": data.nome_completo,
                "endereco": data.endereco,
                "valor_fatura": data.valor_fatura,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado no webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para exceções não tratadas"""
    logger.error(f"Erro não tratado: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "erro",
            "message": "Erro interno do servidor",
            "detail": str(exc)
        }
    )

# Endpoint para servir arquivos da pasta media (opcional, para desenvolvimento)
from fastapi.staticfiles import StaticFiles

# Verificar se a pasta media existe antes de montar
media_path = os.path.join(os.path.dirname(__file__), 'media')
if os.path.exists(media_path):
    app.mount("/media", StaticFiles(directory=media_path), name="media")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)