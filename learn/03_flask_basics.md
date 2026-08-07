# Flask Basics

## या module चे उद्दिष्ट

Flask app कसा सुरू होतो आणि route कसा response देतो हे समजून घेणे.

## महत्वाचे files

- `run.py`: app run करण्यासाठी entry point
- `app/__init__.py`: application factory म्हणजे `create_app()`
- `app/core/routes.py`: `/` आणि `/health` routes
- `app/templates/base.html`: common layout
- `app/templates/core/index.html`: home page

## Code कुठून सुरू होतो?

`python run.py` command दिल्यावर `run.py` मधील `create_app()` call होते. `create_app()` Flask object तयार करते, config load करते, routes register करते आणि app return करते.

## Template कसा render होतो?

`index()` function `render_template("core/index.html")` call करते. `core/index.html` हा `base.html` extend करतो. त्यामुळे common navbar आणि page structure reuse होते.

## Security कुठे वापरली आहे?

Phase 1 मध्ये full security नाही. पण `config.py` मध्ये `SECRET_KEY`, cookie settings आणि future upload size limit यांची तयारी केली आहे. Actual login security Phase 3 मध्ये येईल.

## Test कसा करायचा?

1. `python run.py` run कर.
2. Browser मध्ये `http://127.0.0.1:5000` उघड.
3. `http://127.0.0.1:5000/health` उघड.

## Expected result

Home page वर PRAVA welcome screen दिसेल. Health route JSON मध्ये `status: ok` दाखवेल.

## Viva प्रश्न

Q: Flask route म्हणजे काय?

A: Browser मधून आलेल्या URL request ला कोणते Python function चालवायचे हे सांगणारा mapping म्हणजे route.
