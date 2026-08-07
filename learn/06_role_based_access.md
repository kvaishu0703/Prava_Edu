# Role-Based Access

## या module चे उद्दिष्ट

Admin, Faculty आणि Student यांना फक्त त्यांच्या role नुसार pages access करता यावेत. कोणताही user दुसऱ्या role च्या protected page वर जाऊ नये.

## वापरलेले concepts

- Decorator: existing function वर extra check लावण्याची Python पद्धत
- Authorization: logged-in user ला हा page वापरण्याची permission आहे का हे तपासणे
- Redirect: user ला योग्य page वर पाठवणे

## संबंधित files

- `app/decorators.py`: `roles_required()` decorator
- `app/admin/routes.py`: admin dashboard protected route
- `app/faculty/routes.py`: faculty dashboard protected route
- `app/student/routes.py`: student dashboard protected route

## Route protection कसे काम करते?

उदाहरण:

```python
@admin_bp.get("/dashboard")
@roles_required("admin")
def dashboard():
    ...
```

इथे `roles_required("admin")` आधी current user login आहे का तपासतो. मग user चा role `admin` आहे का तपासतो. Role चुकीचा असेल तर message दाखवून त्या user च्या स्वतःच्या dashboard वर redirect करतो.

## Security log

Phase 3 मध्ये login/logout activity log मध्ये जाते. Unauthorized access साठी पुढच्या security review phase मध्ये अधिक detail logging वाढवू.

## Test steps

1. `admin / Admin@123` ने login कर आणि `/admin/dashboard` पाहा.
2. Logout कर.
3. `student / Student@123` ने login कर.
4. Browser मध्ये manually `/admin/dashboard` उघड.
5. Student ला admin page दिसू नये.

## Practice task

`faculty / Faculty@123` ने login करून `/student/dashboard` उघडण्याचा प्रयत्न कर. Result काय येतो ते note कर.

## Viva प्रश्न

Q: Authentication आणि Authorization मध्ये फरक काय?

A: Authentication म्हणजे user कोण आहे हे तपासणे. Authorization म्हणजे त्या user ला कोणती permission आहे हे तपासणे.
