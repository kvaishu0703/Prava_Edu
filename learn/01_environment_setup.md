# Environment Setup

## या module चे उद्दिष्ट

Local computer वर Flask project run करण्यासाठी Python virtual environment आणि dependencies setup करणे.

## हे का आवश्यक आहे?

Virtual environment मुळे project साठी लागणारी packages वेगळी राहतात. त्यामुळे एका project ची packages दुसऱ्या project ला disturb करत नाहीत.

## Commands

```powershell
cd D:\parava\prava-college-system
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

## Expected output

Terminal मध्ये Flask server सुरू झाल्याचा message दिसेल आणि browser मध्ये `http://127.0.0.1:5000` उघडल्यावर PRAVA welcome page दिसेल.

## Common errors

- `python is not recognized`: Python install नाही किंवा PATH मध्ये नाही.
- `No module named flask`: virtual environment activate करून `pip install -r requirements.txt` पुन्हा run कर.
- Port already in use: `run.py` मध्ये port 5001 करून पाहा.

## Practice task

Virtual environment activate झाल्यावर `pip list` command run करून Flask install झाले आहे का तपास.
