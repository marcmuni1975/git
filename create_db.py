from app import app, db, Alumno, Nota

def reset_db():
    with app.app_context():
        # Elimina todas las tablas existentes
        db.drop_all()
        print("Tablas eliminadas")
        
        # Crea las tablas nuevamente
        db.create_all()
        print("Base de datos creada exitosamente")
        
        # Verifica que las tablas se crearon
        print("\nVerificando tablas:")
        for table in db.metadata.tables.keys():
            print(f"- {table}")

def check_db():
    with app.app_context():
        # Verifica alumnos
        alumnos = Alumno.query.all()
        print("\nAlumnos en la base de datos:")
        for alumno in alumnos:
            print(f"- {alumno.nombre_completo} ({alumno.curso})")
            
            # Verifica notas
            for nota in alumno.notas:
                print(f"  * {nota.asignatura}: {nota.calificaciones}")

if __name__ == "__main__":
    reset_db()
    check_db()