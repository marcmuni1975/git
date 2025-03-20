from app import app, db, Alumno, Nota

def add_test_data():
    with app.app_context():
        # Agregar algunos alumnos de prueba
        alumnos_test = [
            {"nombre": "Juan Pérez González", "curso": "1ro C"},
            {"nombre": "María López Silva", "curso": "1ro C"},
            {"nombre": "Pedro Sánchez Ruiz", "curso": "2do C"}
        ]
        
        for alumno_data in alumnos_test:
            alumno = Alumno(
                nombre_completo=alumno_data["nombre"],
                curso=alumno_data["curso"]
            )
            db.session.add(alumno)
            print(f"Agregando alumno: {alumno.nombre_completo}")
        
        try:
            db.session.commit()
            print("Datos de prueba agregados exitosamente")
        except Exception as e:
            db.session.rollback()
            print(f"Error al agregar datos: {str(e)}")

if __name__ == "__main__":
    add_test_data()