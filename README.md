# 🚀 Soleco: Solana Blockchain Analytics Platform

## 📖 Overview

A comprehensive API aggregator for the Solana ecosystem, integrating multiple protocols including Jupiter, Raydium, Birdeye, Meteora, and more.

## Project Structure

```
soleco/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── jupiter.py
│   │   │   ├── raydium.py
│   │   │   ├── birdeye.py
│   │   │   └── ...
│   │   └── main.py
│   └── requirements.txt
├── cli/
│   ├── soleco_cli/
│   │   ├── api.py
│   │   ├── config.py
│   │   ├── utils.py
│   │   └── ...
│   ├── tests/
│   └── README.md
└── frontend/
    ├── src/
    │   ├── api/
    │   │   └── client.ts
    │   ├── components/
    │   │   ├── JupiterPanel.tsx
    │   │   ├── RaydiumPanel.tsx
    │   │   └── BirdeyePanel.tsx
    │   └── App.tsx
    └── package.json
```

## Setup

### Backend

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the application
```bash
uvicorn app.main:app --reload
```

### CLI

1. Install the CLI tool:
```bash
cd cli
pip install -e .
```

2. Use the CLI:
```bash
soleco --help
```

For detailed CLI documentation, see [CLI README](cli/README.md)

## 📄 Documentation

Full API documentation available at `/docs` when the server is running.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md)

## 💡 Support & Community

- [Discord Community](https://discord.gg/your-discord)
- [Twitter](https://twitter.com/soleco)
- [GitHub Discussions](https://github.com/yourusername/soleco/discussions)

## 📊 Roadmap

- [ ] Implement more API integrations
- [ ] Develop frontend dashboard
- [ ] Add advanced analytics features
- [ ] Implement user authentication

## 📝 License

MIT License

## 💖 Sponsors

[Your sponsorship information]

---

**Disclaimer**: This project is community-driven and not affiliated with Solana Foundation.
