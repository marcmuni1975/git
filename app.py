# Configuración inicial
import os
from datetime import datetime
import locale
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF

# Configurar locale para fechas en español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_CL.UTF-8')
    except:
        print("No se pudo configurar el idioma español para las fechas")

# Configuración de la aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Constantes
ASIGNATURAS = [
    'Matemáticas',
    'Lenguaje',
    'Inglés', 
    'Cs. Sociales',
    'Cs. Naturales',
    'Instrumental'
]

# Modelos
class Curso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    alumnos = db.relationship('Alumno', backref='curso_rel', lazy=True)

    def __repr__(self):
        return self.nombre

class Alumno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(100), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'), nullable=False)
    numero_lista = db.Column(db.Integer)
    notas = db.relationship('Nota', backref='alumno', lazy=True, cascade='all, delete-orphan')

    def obtener_promedio_asignatura(self, asignatura):
        notas_asignatura = [n for n in self.notas if n.asignatura == asignatura]
        if notas_asignatura:
            notas = notas_asignatura[0].lista_calificaciones
            return sum(notas) / len(notas) if notas else 0
        return 0

class Nota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asignatura = db.Column(db.String(50), nullable=False)
    calificaciones = db.Column(db.String(100), nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumno.id'), nullable=False)

    @property
    def lista_calificaciones(self):
        return [float(x) for x in self.calificaciones.split(',') if x.strip()]

# Migración de base de datos
with app.app_context():
    db.drop_all()  # Eliminar tablas existentes
    db.create_all()  # Crear nuevas tablas
    
    # Crear cursos por defecto
    cursos_default = ['1ro C', '2do C']
    for nombre_curso in cursos_default:
        curso = Curso(nombre=nombre_curso)
        db.session.add(curso)
    db.session.commit()

# Clase para generar PDFs
class PDF(FPDF):
    def header(self):
        # Logo en la esquina superior izquierda
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'logo.png')
            if os.path.exists(logo_path):
                self.image(logo_path, x=10, y=8, w=30)  # Logo más pequeño a la izquierda
            else:
                print(f"Logo no encontrado en: {logo_path}")
        except Exception as e:
            print(f"Error al cargar el logo: {e}")
            import traceback
            print(traceback.format_exc())
        
        # Texto del membrete al lado del logo
        self.set_font('Arial', 'B', 15)
        self.set_xy(45, 15)  # Posición al lado del logo
        self.cell(0, 10, 'CEIA Amigos del Padre Hurtado - La Serena', 0, 1, 'L')
        self.ln(20)

    def create_grade_cell(self, w, h, txt, border=1):
        # Método auxiliar para crear celdas de notas con borde completo
        self.cell(w, h, txt, border, 0, 'C')

    def footer(self):
        self.set_y(-30)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, '_'*40, 0, 1, 'C')
        self.cell(0, 10, 'Jefe de UTP', 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

@app.route('/')
def index():
    cursos = Curso.query.order_by(Curso.nombre).all()
    return render_template('index.html', cursos=cursos)

@app.route('/administrar_cursos', methods=['GET', 'POST'])
def administrar_cursos():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if nombre:
            try:
                curso = Curso(nombre=nombre)
                db.session.add(curso)
                db.session.commit()
                flash('Curso agregado exitosamente', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al agregar curso: {str(e)}', 'error')
    
    cursos = Curso.query.order_by(Curso.nombre).all()
    return render_template('administrar_cursos.html', cursos=cursos)

@app.route('/editar_curso/<int:curso_id>', methods=['GET', 'POST'])
def editar_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if nombre:
            try:
                curso.nombre = nombre
                db.session.commit()
                flash('Curso actualizado exitosamente', 'success')
                return redirect(url_for('administrar_cursos'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar curso: {str(e)}', 'error')
    return render_template('editar_curso.html', curso=curso)

@app.route('/eliminar_curso/<int:curso_id>')
def eliminar_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    try:
        db.session.delete(curso)
        db.session.commit()
        flash('Curso eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar curso: {str(e)}', 'error')
    return redirect(url_for('administrar_cursos'))

@app.route('/administrar_alumnos/<int:curso_id>', methods=['GET', 'POST'])
def administrar_alumnos(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if nombre:
            try:
                # Obtener el último número de lista
                ultimo_alumno = Alumno.query.filter_by(curso_id=curso_id).order_by(Alumno.numero_lista.desc()).first()
                nuevo_numero = (ultimo_alumno.numero_lista + 1) if ultimo_alumno else 1
                
                # Formatear nombre
                nombre_formateado = ' '.join(palabra.capitalize() for palabra in nombre.strip().split())
                
                # Crear nuevo alumno
                alumno = Alumno(
                    nombre_completo=nombre_formateado,
                    curso_id=curso_id,
                    numero_lista=nuevo_numero
                )
                db.session.add(alumno)
                db.session.commit()
                flash('Alumno agregado exitosamente', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al agregar alumno: {str(e)}', 'error')
    
    alumnos = Alumno.query.filter_by(curso_id=curso_id).order_by(Alumno.numero_lista).all()
    return render_template('administrar_alumnos.html', curso=curso, alumnos=alumnos)

@app.route('/editar_alumno/<int:alumno_id>', methods=['GET', 'POST'])
def editar_alumno(alumno_id):
    alumno = Alumno.query.get_or_404(alumno_id)
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        numero_lista = request.form.get('numero_lista')
        if nombre and numero_lista:
            try:
                alumno.nombre_completo = nombre
                alumno.numero_lista = int(numero_lista)
                db.session.commit()
                flash('Alumno actualizado exitosamente', 'success')
                return redirect(url_for('administrar_alumnos', curso_id=alumno.curso_id))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar alumno: {str(e)}', 'error')
    return render_template('editar_alumno.html', alumno=alumno)

@app.route('/eliminar_alumno/<int:alumno_id>')
def eliminar_alumno(alumno_id):
    alumno = Alumno.query.get_or_404(alumno_id)
    curso_id = alumno.curso_id
    try:
        db.session.delete(alumno)
        db.session.commit()
        flash('Alumno eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar alumno: {str(e)}', 'error')
    return redirect(url_for('administrar_alumnos', curso_id=curso_id))

@app.route('/importar_alumnos/<int:curso_id>', methods=['GET', 'POST'])
def importar_alumnos(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    if request.method == 'POST':
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        archivo = request.files['archivo']
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        if archivo:
            try:
                contenido = archivo.read().decode('utf-8')
                lineas = contenido.strip().split('\n')
                for i, linea in enumerate(lineas, 1):
                    nombre = linea.strip()
                    if nombre:
                        alumno = Alumno(
                            nombre_completo=nombre,
                            curso_id=curso_id,
                            numero_lista=i
                        )
                        db.session.add(alumno)
                
                db.session.commit()
                flash(f'Se importaron {len(lineas)} alumnos exitosamente', 'success')
                return redirect(url_for('administrar_alumnos', curso_id=curso_id))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al importar alumnos: {str(e)}', 'error')
    
    return render_template('importar_alumnos.html', curso=curso)

@app.route('/editar_notas/<int:alumno_id>')
def editar_notas(alumno_id):
    alumno = Alumno.query.get_or_404(alumno_id)
    notas_por_asignatura = {}
    for asignatura in ASIGNATURAS:
        nota = Nota.query.filter_by(alumno_id=alumno_id, asignatura=asignatura).first()
        if nota:
            notas_por_asignatura[asignatura] = nota.lista_calificaciones
        else:
            notas_por_asignatura[asignatura] = []
    
    return render_template('editar_notas.html', alumno=alumno, asignaturas=ASIGNATURAS, notas=notas_por_asignatura)

@app.route('/actualizar_nota/<int:alumno_id>/<asignatura>', methods=['POST'])
def actualizar_nota(alumno_id, asignatura):
    try:
        notas_str = request.form.get('notas')
        if notas_str:
            notas = [float(n.strip()) for n in notas_str.split(',') if n.strip()]
            nota = Nota.query.filter_by(alumno_id=alumno_id, asignatura=asignatura).first()
            if nota:
                nota.calificaciones = ','.join(str(n) for n in notas)
            else:
                nota = Nota(
                    asignatura=asignatura,
                    calificaciones=','.join(str(n) for n in notas),
                    alumno_id=alumno_id
                )
                db.session.add(nota)
            
            db.session.commit()
            flash('Notas actualizadas exitosamente', 'success')
        else:
            # Si no hay notas, eliminar el registro si existe
            nota = Nota.query.filter_by(alumno_id=alumno_id, asignatura=asignatura).first()
            if nota:
                db.session.delete(nota)
                db.session.commit()
            flash('Notas eliminadas', 'success')
    except ValueError:
        flash('Error en el formato de las notas', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar notas: {str(e)}', 'error')
    
    return redirect(url_for('editar_notas', alumno_id=alumno_id))

@app.route('/exportar_curso_pdf/<int:curso_id>')
def exportar_curso_pdf(curso_id):
    try:
        curso = Curso.query.get_or_404(curso_id)
        alumnos = Alumno.query.filter_by(curso_id=curso_id)\
                             .order_by(Alumno.numero_lista)\
                             .all()
        
        pdf = PDF()
        pdf.add_page()
        
        # Establecer márgenes uniformes
        margin = 20
        pdf.set_margins(margin, margin, margin)
        pdf.set_auto_page_break(True, margin)
        
        pdf.ln(20)  # Espacio después del membrete
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'Informe de Notas - {curso.nombre}', 0, 1, 'C')
        pdf.ln(10)
        
        # Configuración de la tabla
        page_width = pdf.w - 2*margin
        
        # Distribución del ancho de columnas
        col_width_numero = page_width * 0.05  # 5% para número de lista
        col_width_nombre = page_width * 0.25  # 25% para nombre
        col_width_nota = page_width * 0.07    # 7% para cada nota (total 42% para 6 notas)
        col_width_promedio = page_width * 0.08  # 8% para promedio
        
        # Altura de fila uniforme
        row_height = 7
        
        # Encabezados
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(col_width_numero, row_height, 'N°', 1, 0, 'C')
        pdf.cell(col_width_nombre, row_height, 'Nombre', 1, 0, 'C')
        
        for asignatura in ASIGNATURAS:
            pdf.cell(col_width_nota, row_height, asignatura[:4], 1, 0, 'C')
        
        pdf.cell(col_width_promedio, row_height, 'Prom.', 1, 1, 'C')
        
        # Datos de alumnos
        pdf.set_font('Arial', '', 10)
        
        promedios_curso = []
        for alumno in alumnos:
            # Número de lista
            pdf.cell(col_width_numero, row_height, str(alumno.numero_lista), 1, 0, 'C')
            
            # Nombre del alumno
            pdf.cell(col_width_nombre, row_height, alumno.nombre_completo, 1, 0, 'L')
            
            # Promedios por asignatura
            promedios_alumno = []
            for asignatura in ASIGNATURAS:
                promedio = alumno.obtener_promedio_asignatura(asignatura)
                promedios_alumno.append(promedio)
                pdf.cell(col_width_nota, row_height, f'{promedio:.1f}', 1, 0, 'C')
            
            # Promedio del alumno
            promedio_alumno = sum(promedios_alumno) / len(promedios_alumno) if promedios_alumno else 0
            promedios_curso.append(promedio_alumno)
            pdf.cell(col_width_promedio, row_height, f'{promedio_alumno:.1f}', 1, 1, 'C')
        
        # Promedio del curso
        pdf.ln(5)
        promedio_curso = sum(promedios_curso) / len(promedios_curso) if promedios_curso else 0
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 10, f'Promedio del Curso: {promedio_curso:.1f}', 0, 1, 'C')
        
        # Guardar PDF
        os.makedirs('static/pdfs', exist_ok=True)
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'notas_{curso.nombre.replace(" ", "_")}_{fecha}.pdf'
        pdf_path = os.path.join('static', 'pdfs', filename)
        pdf.output(pdf_path)
        
        return send_file(pdf_path, as_attachment=True)
        
    except Exception as e:
        print(f"Error al generar PDF: {e}")
        flash('Error al generar el PDF', 'error')
        return redirect(url_for('administrar_alumnos', curso_id=curso_id))

@app.route('/certificado_alumno/<int:alumno_id>')
def certificado_alumno(alumno_id):
    try:
        alumno = Alumno.query.get_or_404(alumno_id)
        
        pdf = PDF()
        pdf.add_page()
        
        # Establecer márgenes uniformes
        margin = 20
        pdf.set_margins(margin, margin, margin)
        pdf.set_auto_page_break(True, margin)
        
        pdf.ln(20)  # Espacio después del membrete
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'CERTIFICADO DE NOTAS', 0, 1, 'C')
        pdf.ln(10)
        
        # Información del alumno
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Certifico que el alumno(a):', 0, 1)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f'{alumno.nombre_completo}', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Del curso {alumno.curso_rel.nombre}, tiene las siguientes calificaciones:', 0, 1)
        pdf.ln(10)
        
        # Configuración de la tabla
        page_width = pdf.w - 2*margin
        max_notas = 7  # N1 a N7
        
        # Calcular anchos de columna basados en el espacio disponible
        col_width_asignatura = page_width * 0.25  # 25% del espacio disponible
        col_width_nota = (page_width * 0.65) / max_notas  # 65% distribuido entre las notas
        col_width_promedio = page_width * 0.10  # 10% para el promedio
        row_height = 7
        
        # Encabezados
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(col_width_asignatura, row_height, 'Asignatura', 1, 0, 'C')
        
        # Encabezados numerados para las notas
        for i in range(max_notas):
            pdf.cell(col_width_nota, row_height, f'N{i+1}', 1, 0, 'C')
        
        pdf.cell(col_width_promedio, row_height, 'Prom.', 1, 1, 'C')
        
        # Datos
        pdf.set_font('Arial', '', 10)
        promedios = []
        
        for asignatura in ASIGNATURAS:
            notas = [n for n in alumno.notas if n.asignatura == asignatura]
            promedio = alumno.obtener_promedio_asignatura(asignatura)
            promedios.append(promedio)
            
            # Asignatura (alineada a la izquierda con un pequeño padding)
            pdf.cell(col_width_asignatura, row_height, ' ' + asignatura, 1, 0, 'L')
            
            # Notas en celdas individuales
            if notas:
                notas_lista = notas[0].lista_calificaciones
                # Rellenar celdas con notas o vacías
                for i in range(max_notas):
                    if i < len(notas_lista):
                        pdf.cell(col_width_nota, row_height, f'{notas_lista[i]:.1f}', 1, 0, 'C')
                    else:
                        pdf.cell(col_width_nota, row_height, '', 1, 0, 'C')
            else:
                # Si no hay notas, crear celdas vacías
                for _ in range(max_notas):
                    pdf.cell(col_width_nota, row_height, '', 1, 0, 'C')
            
            # Promedio
            pdf.cell(col_width_promedio, row_height, f'{promedio:.1f}', 1, 1, 'C')
        
        # Promedio final
        pdf.ln(10)
        promedio_final = sum(promedios) / len(promedios) if promedios else 0
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f'Promedio Final: {promedio_final:.1f}', 0, 1, 'C')
        
        # Fecha
        pdf.ln(10)
        pdf.set_font('Arial', '', 10)
        fecha_actual = datetime.now().strftime('%d de %B de %Y').capitalize()
        pdf.cell(0, 10, f'La Serena, {fecha_actual}', 0, 1)
        
        # Guardar PDF
        os.makedirs('static/pdfs', exist_ok=True)
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'certificado_{alumno.nombre_completo.replace(" ", "_")}_{fecha}.pdf'
        pdf_path = os.path.join('static', 'pdfs', filename)
        pdf.output(pdf_path)
        
        return send_file(pdf_path, as_attachment=True, download_name=filename)
    
    except Exception as e:
        print(f"Error al generar certificado: {e}")
        flash('Error al generar el certificado', 'error')
        return redirect(url_for('administrar_alumnos', curso_id=alumno.curso_id))

if __name__ == '__main__':
    app.run(debug=True, port=5004)