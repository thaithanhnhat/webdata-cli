# WebData CLI

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AI Optimized](https://img.shields.io/badge/AI-Optimized-green.svg)](https://github.com/thaithanhnhat/webdata-cli)

🚀 **Powerful web automation tool for AI Agents** - Chrome automation, data extraction, and real-time interface monitoring.

## ✨ What WebData CLI Can Do

### 🤖 For AI Agents
- **See web pages like humans**: Auto-captures interface state + screenshots when navigating
- **Understand any website**: Extracts forms, buttons, links, text content automatically
- **Control Chrome remotely**: Full browser automation via simple commands
- **Get real-time data**: Streams page information directly to terminal for instant AI processing

### 🚀 For Developers
- **Zero-config setup**: Works immediately after installation
- **One-command integration**: Add to any AI project instantly
- **Global access**: Use from anywhere on your system
- **Smart data management**: Automatic cleanup, fixed file paths

## 📦 Installation

```bash
pip install git+https://github.com/thaithanhnhat/webdata-cli.git
```

### Verify Installation
```bash
webdata --help
```

## 🚀 Quick Start

```bash
# 1. Install
pip install git+https://github.com/thaithanhnhat/webdata-cli.git

# 2. Integrate with your AI project
cd /your/ai/project
webdata integrate --project-path .

# 3. Your AI can now use it
webdata start-chrome
webdata remote get "https://example.com" --stream
# AI gets: interface_state + screenshot automatically
```

**That's it!** Your AI project now has web automation capabilities.

## 🎯 Current Version Capabilities

### ✅ Web Automation
- **Chrome control**: Start, navigate, interact with any website
- **Form automation**: Fill forms, click buttons, submit data
- **Data extraction**: Get text, HTML, network requests, page structure
- **Screenshot capture**: Automatic visual documentation

### ✅ AI Integration
- **Auto interface analysis**: Captures page state automatically when navigating
- **Streaming data**: Real-time information flow to AI via terminal
- **Structured output**: JSON format for easy AI processing
- **Visual context**: Screenshots saved to fixed location for AI reference

### ✅ Developer Experience
- **One-command setup**: `webdata integrate` adds to any project
- **Global access**: Works from any directory after installation
- **Smart cleanup**: Automatic data management, no accumulation
- **Zero configuration**: Works immediately, no setup required

## 💡 Why Choose WebData CLI

**The only web automation tool designed specifically for AI Agents:**

- 🧠 **AI gets full context**: Interface state + visual screenshot automatically
- ⚡ **Real-time data flow**: No file reading delays, direct terminal streaming
- 🎯 **Zero learning curve**: One integration command, AI reads guide and starts working
- 🔧 **Production ready**: Smart cleanup, fixed paths, reliable Chrome management

## 🎯 Use Cases

### AI Web Automation
- **Form filling**: AI reads form structure and fills automatically
- **Data extraction**: Extract structured data from any website
- **Testing**: Automated UI testing with AI verification
- **Monitoring**: Monitor website changes and alerts

### AI Research & Analysis
- **Content analysis**: Extract and analyze web content
- **Competitor research**: Automated competitor monitoring
- **Market research**: Gather data from multiple sources
- **Social media**: Monitor and analyze social platforms

### AI Development & Training
- **Dataset creation**: Generate training data from web sources
- **Model testing**: Test AI models on real web interfaces
- **Workflow automation**: Automate repetitive web tasks
- **Integration testing**: Test AI integrations with web services



## 📁 Project Structure After Integration

```
your-ai-project/
├── AI_INTEGRATION_GUIDE.md   # AI instructions (auto-generated)
├── data/
│   └── current-interface.jpg  # Latest screenshot (auto-updated)
└── your-ai-code.py
```

### How AI Agents Use It

```python
# Python AI Agent
result = subprocess.run(["webdata", "remote", "get", "https://site.com", "--stream"],
                       capture_output=True, text=True)
interface_data = json.loads(result.stdout)
# AI now knows: forms, buttons, links, page content + has screenshot
```

```javascript
// Node.js AI Agent
exec('webdata remote get "https://site.com" --stream', (error, stdout) => {
    const data = JSON.parse(stdout);
    // AI processes interface_state and screenshot path
});
```

## 🛠️ Requirements

- **Python 3.7+**
- **Chrome Browser** (automatically detected)
- **Dependencies**: Automatically installed with pip

## 🗑️ Uninstall

```bash
# Complete removal (package + all data)
webdata uninstall

# Or manual removal
pip uninstall webdata-cli
```

## 🔧 Common Issues

- **Command not found**: Check `pip show webdata-cli` and PATH setup
- **Chrome issues**: Install Chrome browser, run `webdata check-chrome`
- **Permission errors**: Use `pip install --user git+https://github.com/thaithanhnhat/webdata-cli.git`

For detailed troubleshooting: `webdata --help`

## 🤝 Contributing

1. Fork the repository: https://github.com/thaithanhnhat/webdata-cli
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 **Documentation**: Check `AI_INTEGRATION_GUIDE.md` after integration
- 🐛 **Issues**: Create GitHub Issues for bugs and feature requests
- 💬 **Questions**: Use GitHub Discussions for questions and help
- 📧 **Contact**: For enterprise support and custom integrations

---

**Made for AI Agents** 🤖 | **Easy Integration** ⚡ | **Powerful Automation** 🚀
