# EasyTracker

Aplicação web em Flask para registrar refeições e acompanhar **proteínas, carboidratos, gorduras e calorias** do dia. Os valores nutricionais são estimados com **Google Gemini**.

## Funcionalidades

- Registrar refeições em linguagem natural (ex.: *“2 ovos, pão integral e café”*)
- Acumular macros e calorias na sessão do dia
- Interface web simples e responsiva

## Pré-requisitos

- Python 3.11+
- [Chave de API do Gemini](https://aistudio.google.com/apikey)

## Instalação

```bash
git clone https://github.com/SEU_USUARIO/easytracker.git
cd easytracker

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

Edite o arquivo `.env` e coloque sua chave (uma linha por variável, **sem aspas**):

```env
GOOGLE_API_KEY=AIza...
FLASK_SECRET_KEY=qualquer-string-secreta-longa
```

## Executar

```bash
cd src
python app.py
```

Abra no navegador: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Estrutura do projeto

```
easytracker/
├── src/
│   ├── app.py            # Rotas Flask e interface
│   └── ai_processing.py  # Integração com Gemini
├── .env.example
├── requirements.txt
└── README.md
```

## Aviso

As estimativas nutricionais são geradas por IA e servem apenas como **referência aproximada**, não como orientação médica ou nutricional profissional.

## Licença

MIT — veja [LICENSE](LICENSE).
