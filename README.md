# 📄 Exportador de Propostas - Energia Solar (Integração Node.js)

Módulo Python para geração automatizada de propostas comerciais em PDF para projetos de energia solar fotovoltaica, projetado para integração com aplicações Node.js.

## 🌟 Características Principais

- **Integração Node.js**: Execução via child_process do Node.js
- **Geração Automática de PDFs**: Criação de propostas profissionais em formato PDF
- **Cálculos Financeiros Automáticos**: Análise completa de economia com energia solar
- **Gráficos Comparativos**: Visualização clara da economia entre cenários com e sem energia solar
- **Análise de Bandeiras Tarifárias**: Cálculo de economia considerando diferentes bandeiras da ANEEL
- **API Simples**: Interface de linha de comando para fácil integração

## 🚀 Funcionalidades

### ✨ Entrada de Dados via Parâmetros
- **Nome Completo**: Nome do cliente
- **Endereço Completo**: Endereço da instalação  
- **Valor da Fatura**: Valor atual da conta de energia

### 📊 Cálculos Automáticos
- Consumo total baseado no valor da fatura
- Taxa de iluminação pública ajustada
- Consumo mínimo otimizado
- Tarifas com desconto aplicado
- Economia mensal, anual e em 5 anos

### 📈 Análises Incluídas
- Comparação "Sem Geração Solar" vs "Com Geração Solar"
- Impacto das bandeiras tarifárias (Amarela, Vermelha P1/P2, Escassez Hídrica)
- Breakdown detalhado dos custos
- Projeções financeiras de longo prazo

## 🛠️ Stack Tecnológico

### Backend Python
- **Python 3.x**: Engine de processamento
- **ReportLab**: Geração de PDFs profissionais
- **Matplotlib**: Criação de gráficos comparativos
- **NumPy**: Cálculos matemáticos e estatísticos

### Integração Node.js
- **child_process**: Execução do script Python
- **fs**: Manipulação de arquivos gerados
- **path**: Gerenciamento de caminhos

## 📋 Pré-requisitos

- **Node.js** 14.x ou superior
- **Python** 3.7 ou superior
- **npm** ou **yarn**

## ⚙️ Instalação no Projeto Node.js

### 1. Configuração do Ambiente Python

```bash
# Navegue até o diretório do módulo Python
cd proposta_exportar

# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale as dependências Python
pip install -r requirements.txt
```

### 2. Integração com Node.js

Adicione este módulo ao seu projeto Node.js:

```javascript
// services/propostaService.js
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs').promises;

class PropostaService {
  constructor() {
    this.pythonPath = path.join(__dirname, '../proposta_exportar/venv/Scripts/python.exe'); // Windows
    // this.pythonPath = path.join(__dirname, '../proposta_exportar/venv/bin/python'); // Linux/Mac
    this.scriptPath = path.join(__dirname, '../proposta_exportar/proposta.py');
  }

  async gerarProposta(dadosCliente) {
    const { nome, endereco, valorFatura } = dadosCliente;
    
    return new Promise((resolve, reject) => {
      const pythonProcess = spawn(this.pythonPath, [
        this.scriptPath,
        nome,
        endereco,
        valorFatura.toString()
      ]);

      let output = '';
      let error = '';

      pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        error += data.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          // Extrair caminho do arquivo gerado do output
          const match = output.match(/Proposta salva em: (.+\.pdf)/);
          if (match) {
            resolve({
              success: true,
              filePath: match[1],
              output: output
            });
          } else {
            reject(new Error('Não foi possível encontrar o arquivo gerado'));
          }
        } else {
          reject(new Error(`Erro na execução: ${error}`));
        }
      });
    });
  }

  async verificarArquivo(filePath) {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }
}

module.exports = PropostaService;
```

### 3. Uso no Controller/Route

```javascript
// controllers/propostaController.js
const PropostaService = require('../services/propostaService');

const propostaService = new PropostaService();

exports.gerarProposta = async (req, res) => {
  try {
    const { nome, endereco, valorFatura } = req.body;

    // Validação dos dados
    if (!nome || !endereco || !valorFatura) {
      return res.status(400).json({
        error: 'Dados obrigatórios: nome, endereco, valorFatura'
      });
    }

    // Gerar proposta
    const resultado = await propostaService.gerarProposta({
      nome,
      endereco,
      valorFatura: parseFloat(valorFatura)
    });

    // Verificar se arquivo foi criado
    const arquivoExiste = await propostaService.verificarArquivo(resultado.filePath);
    
    if (!arquivoExiste) {
      throw new Error('Arquivo PDF não foi criado');
    }

    res.json({
      success: true,
      message: 'Proposta gerada com sucesso',
      filePath: resultado.filePath,
      fileName: path.basename(resultado.filePath)
    });

  } catch (error) {
    console.error('Erro ao gerar proposta:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      details: error.message
    });
  }
};
```

### 4. Rota Express

```javascript
// routes/propostas.js
const express = require('express');
const router = express.Router();
const propostaController = require('../controllers/propostaController');

router.post('/gerar', propostaController.gerarProposta);

module.exports = router;
```

## 🎯 Como Usar no Node.js

### Exemplo de Requisição

```javascript
// Exemplo de uso
const dadosCliente = {
  nome: "João da Silva Santos",
  endereco: "Rua das Flores, 124 - Centro - Campo Grande/MS",
  valorFatura: 439.85
};

// POST /api/propostas/gerar
fetch('/api/propostas/gerar', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(dadosCliente)
})
.then(response => response.json())
.then(data => {
  console.log('Proposta gerada:', data.fileName);
  console.log('Caminho:', data.filePath);
});
```

### Resposta da API

```json
{
  "success": true,
  "message": "Proposta gerada com sucesso",
  "filePath": "proposta_exportar/propostas/proposta_João_da_Silva_Santos_20250127_161241.pdf",
  "fileName": "proposta_João_da_Silva_Santos_20250127_161241.pdf"
}
```

## 📁 Estrutura do Projeto

```
projeto-node/
├── proposta_exportar/          # Módulo Python
│   ├── proposta.py            # Script principal (modificado para CLI)
│   ├── requirements.txt       # Dependências Python
│   ├── fonts/                 # Fontes para o PDF
│   ├── img/                   # Imagens e gráficos
│   ├── propostas/             # PDFs gerados
│   └── venv/                  # Ambiente virtual Python
├── services/
│   └── propostaService.js     # Service de integração
├── controllers/
│   └── propostaController.js  # Controller da API
├── routes/
│   └── propostas.js           # Rotas da API
└── package.json               # Dependências Node.js
```

## 🔧 Modificações Necessárias no Script Python

Para funcionar com Node.js, o script `proposta.py` precisa ser modificado para aceitar argumentos de linha de comando. Adicione no início do arquivo:

```python
import sys

# Verificar se argumentos foram passados
if len(sys.argv) >= 4:
    nome = sys.argv[1]
    endereco = sys.argv[2] 
    valor_fatura = float(sys.argv[3])
else:
    # Valores padrão para teste local
    nome = "Marcos da Silva Santos Odete"
    endereco = "Rua das Flores, 124 - Centro - Campo Grande/MS"
    valor_fatura = 439.85
```

## 📊 Fluxo de Execução

1. **Requisição HTTP** → Controller Node.js
2. **Validação** → Dados do cliente
3. **Spawn Process** → Execução do script Python
4. **Geração PDF** → Arquivo salvo em `/propostas`
5. **Resposta JSON** → Caminho do arquivo gerado

## 🔒 Tratamento de Erros

### Erros Comuns e Soluções

```javascript
// Exemplo de tratamento robusto
try {
  const resultado = await propostaService.gerarProposta(dadosCliente);
} catch (error) {
  if (error.message.includes('Python não encontrado')) {
    // Verificar instalação do Python
    console.error('Python não está instalado ou não está no PATH');
  } else if (error.message.includes('Módulo não encontrado')) {
    // Verificar dependências
    console.error('Dependências Python não instaladas');
  } else {
    // Erro genérico
    console.error('Erro na geração:', error.message);
  }
}
```

### Validações Recomendadas

```javascript
// Validação de entrada
const validarDados = (dados) => {
  const erros = [];
  
  if (!dados.nome || dados.nome.length < 3) {
    erros.push('Nome deve ter pelo menos 3 caracteres');
  }
  
  if (!dados.endereco || dados.endereco.length < 10) {
    erros.push('Endereço deve ser completo');
  }
  
  if (!dados.valorFatura || dados.valorFatura <= 0) {
    erros.push('Valor da fatura deve ser maior que zero');
  }
  
  return erros;
};
```

## 🚀 Deploy e Produção

### Variáveis de Ambiente

```javascript
// .env
PYTHON_PATH=/path/to/python
PROPOSTA_SCRIPT_PATH=/path/to/proposta.py
PROPOSTAS_OUTPUT_DIR=/path/to/propostas
```

### Configuração para Produção

```javascript
// config/proposta.js
module.exports = {
  pythonPath: process.env.PYTHON_PATH || 'python',
  scriptPath: process.env.PROPOSTA_SCRIPT_PATH || './proposta_exportar/proposta.py',
  outputDir: process.env.PROPOSTAS_OUTPUT_DIR || './proposta_exportar/propostas',
  timeout: 30000 // 30 segundos timeout
};
```

## 📈 Performance e Otimização

### Processamento Assíncrono

```javascript
// Queue para processamento em lote
const Queue = require('bull');
const propostaQueue = new Queue('proposta generation');

propostaQueue.process(async (job) => {
  const { dadosCliente } = job.data;
  return await propostaService.gerarProposta(dadosCliente);
});

// Uso
exports.gerarPropostaAsync = async (req, res) => {
  const job = await propostaQueue.add('gerar', { 
    dadosCliente: req.body 
  });
  
  res.json({ 
    jobId: job.id, 
    status: 'processing' 
  });
};
```

### Cache de Resultados

```javascript
// Cache simples com Redis
const redis = require('redis');
const client = redis.createClient();

const getCacheKey = (dados) => {
  return `proposta:${dados.nome}:${dados.valorFatura}`;
};

// Verificar cache antes de gerar
const cacheKey = getCacheKey(dadosCliente);
const cached = await client.get(cacheKey);

if (cached) {
  return JSON.parse(cached);
}
```

## 🧪 Testes

### Teste Unitário do Service

```javascript
// tests/propostaService.test.js
const PropostaService = require('../services/propostaService');

describe('PropostaService', () => {
  let service;
  
  beforeEach(() => {
    service = new PropostaService();
  });
  
  test('deve gerar proposta com dados válidos', async () => {
    const dados = {
      nome: 'João Silva',
      endereco: 'Rua Teste, 123',
      valorFatura: 300.50
    };
    
    const resultado = await service.gerarProposta(dados);
    
    expect(resultado.success).toBe(true);
    expect(resultado.filePath).toContain('.pdf');
  });
});
```

## 📋 Dependências Node.js

Adicione ao seu `package.json`:

```json
{
  "dependencies": {
    "express": "^4.18.0",
    "bull": "^4.10.0",
    "redis": "^4.6.0"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "supertest": "^6.3.0"
  }
}
```

## 📝 Dependências Python

```
charset-normalizer==3.4.2
contourpy==1.3.3
cycler==0.12.1
fonttools==4.59.0
kiwisolver==1.4.8
matplotlib==3.10.3
numpy==2.3.2
packaging==25.0
pillow==11.3.0
pyparsing==3.2.3
python-dateutil==2.9.0.post0
reportlab==4.4.3
six==1.17.0
```

## 🔧 Solução de Problemas

### Problemas Comuns na Integração

#### 1. Python não encontrado
```bash
# Verificar se Python está no PATH
python --version
# ou
python3 --version

# No Windows, pode ser necessário usar:
py --version
```

#### 2. Erro de permissões no ambiente virtual
```bash
# Windows - executar como administrador
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Linux/Mac - verificar permissões
chmod +x venv/bin/python
```

#### 3. Módulos Python não encontrados
```bash
# Reinstalar dependências
cd proposta_exportar
pip install -r requirements.txt --force-reinstall
```

#### 4. Timeout na execução
```javascript
// Aumentar timeout no service
const pythonProcess = spawn(this.pythonPath, args, {
  timeout: 60000 // 60 segundos
});
```

### Logs e Debug

```javascript
// Adicionar logs detalhados
console.log('Executando:', this.pythonPath, args);
console.log('Diretório de trabalho:', process.cwd());

pythonProcess.stdout.on('data', (data) => {
  console.log('Python stdout:', data.toString());
});

pythonProcess.stderr.on('data', (data) => {
  console.error('Python stderr:', data.toString());
});
```

## 🚀 Exemplo Completo de Implementação

### Estrutura Mínima do Projeto Node.js

```javascript
// app.js
const express = require('express');
const path = require('path');
const propostaRoutes = require('./routes/propostas');

const app = express();

app.use(express.json());
app.use('/api/propostas', propostaRoutes);

// Servir arquivos PDF gerados
app.use('/downloads', express.static(path.join(__dirname, 'proposta_exportar/propostas')));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor rodando na porta ${PORT}`);
});
```

### Frontend de Exemplo

```html
<!-- public/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Gerador de Propostas</title>
</head>
<body>
    <form id="propostaForm">
        <input type="text" id="nome" placeholder="Nome do Cliente" required>
        <input type="text" id="endereco" placeholder="Endereço Completo" required>
        <input type="number" id="valorFatura" placeholder="Valor da Fatura" step="0.01" required>
        <button type="submit">Gerar Proposta</button>
    </form>

    <script>
        document.getElementById('propostaForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const dados = {
                nome: document.getElementById('nome').value,
                endereco: document.getElementById('endereco').value,
                valorFatura: parseFloat(document.getElementById('valorFatura').value)
            };

            try {
                const response = await fetch('/api/propostas/gerar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dados)
                });

                const result = await response.json();
                
                if (result.success) {
                    // Download do arquivo
                    window.open(`/downloads/${result.fileName}`, '_blank');
                } else {
                    alert('Erro: ' + result.error);
                }
            } catch (error) {
                alert('Erro na requisição: ' + error.message);
            }
        });
    </script>
</body>
</html>
```

## 📊 Monitoramento e Métricas

### Logs Estruturados

```javascript
// utils/logger.js
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'logs/propostas.log' }),
    new winston.transports.Console()
  ]
});

module.exports = logger;
```

### Métricas de Performance

```javascript
// middleware/metrics.js
const logger = require('../utils/logger');

const metricsMiddleware = (req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info('Request completed', {
      method: req.method,
      url: req.url,
      statusCode: res.statusCode,
      duration: `${duration}ms`
    });
  });
  
  next();
};

module.exports = metricsMiddleware;
```

## 🤝 Contribuição

Para contribuir com este módulo de integração:

1. **Fork o repositório**
2. **Crie uma branch para sua feature**
   ```bash
   git checkout -b feature/nova-integracao
   ```
3. **Implemente suas mudanças**
   - Mantenha compatibilidade com Node.js 14+
   - Adicione testes para novas funcionalidades
   - Documente mudanças na API
4. **Execute os testes**
   ```bash
   npm test
   ```
5. **Commit suas mudanças**
   ```bash
   git commit -am 'Adiciona nova funcionalidade de integração'
   ```
6. **Push para a branch**
   ```bash
   git push origin feature/nova-integracao
   ```
7. **Abra um Pull Request**

### Guidelines de Contribuição

- **Código**: Siga as convenções do ESLint
- **Testes**: Mantenha cobertura acima de 80%
- **Documentação**: Atualize o README para novas features
- **Compatibilidade**: Teste em Windows, Linux e macOS

## 📄 Licença

Este projeto é de uso interno. Todos os direitos reservados.

## 📞 Suporte Técnico

### Para Desenvolvedores
- **Issues**: Reporte bugs via GitHub Issues
- **Documentação**: Wiki do projeto
- **Chat**: Slack #dev-propostas

### Para Usuários Finais
- **WhatsApp**: (67) 9 9343-1808
- **Email**: suporte@empresa.com
- **Horário**: Segunda a Sexta, 8h às 18h

## 🔄 Versionamento

Este projeto segue o [Semantic Versioning](https://semver.org/):

- **MAJOR**: Mudanças incompatíveis na API
- **MINOR**: Novas funcionalidades compatíveis
- **PATCH**: Correções de bugs

### Changelog

- **v1.0.0**: Versão inicial com integração Node.js
- **v1.1.0**: Adicionado suporte a processamento assíncrono
- **v1.2.0**: Implementado cache Redis

---

**Desenvolvido para integração perfeita entre Node.js e Python** 🚀⚡

*Transformando dados em propostas profissionais com a velocidade do Node.js e a robustez do Python* 🌞📊