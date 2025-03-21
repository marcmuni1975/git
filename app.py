from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from fpdf import FPDF
import os
import locale

# Configurar locale para fechas en español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish')
    except:
        print("No se pudo configurar el idioma español para las fechas")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'clave-secreta-123'
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

CURSOS = ['1ro C', '2do C']

class Alumno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(100), nullable=False)
    curso = db.Column(db.String(50), nullable=False)
    notas = db.relationship('Nota', backref='alumno', lazy=True)

    def obtener_promedio_asignatura(self, asignatura):
        notas_asignatura = [n for n in self.notas if n.asignatura == asignatura]
        if notas_asignatura:
            notas = notas_asignatura[0].lista_calificaciones
            return sum(notas) / len(notas) if notas else 0
        return 0

class Nota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asignatura = db.Column(db.String(50), nullable=False)
    calificaciones = db.Column(db.String(200))
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumno.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def lista_calificaciones(self):
        if self.calificaciones:
            return [float(x) for x in self.calificaciones.split(',') if x.strip()]
        return []

class PDF(FPDF):
    def header(self):
        # Logo
        try:
            if os.path.exists(os.path.join('static', 'logo.png')):
                self.image(os.path.join('static', 'logo.png'), 10, 8, 33)
        except Exception as e:
            print(f"Error al cargar el logo: {e}")
        
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'CEIA Amigos del Padre Hurtado - La Serena', 0, 1, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-30)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, '_'*40, 0, 1, 'C')
        self.cell(0, 10, 'Jefe de UTP', 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

@app.route('/')
def index():
    cursos_info = {}
    for curso in CURSOS:
        count = Alumno.query.filter_by(curso=curso).count()
        cursos_info[curso] = count
    return render_template('index.html', cursos=cursos_info)

@app.route('/curso/<curso>')
def ver_curso(curso):
    if curso not in CURSOS:
        flash('Curso no válido', 'error')
        return redirect(url_for('index'))
    
    alumnos = Alumno.query.filter_by(curso=curso)\
                         .order_by(Alumno.nombre_completo)\
                         .all()
    
    return render_template('curso.html', 
                         curso=curso, 
                         alumnos=alumnos, 
                         asignaturas=ASIGNATURAS)

@app.route('/agregar_alumno/<curso>', methods=['GET', 'POST'])
def agregar_alumno(curso):
    if curso not in CURSOS:
        flash('Curso no válido', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        
        if nombre:
            try:
                nombre_formateado = ' '.join(
                    palabra.capitalize() 
                    for palabra in nombre.strip().split()
                )
                nuevo_alumno = Alumno(nombre_completo=nombre_formateado, curso=curso)
                db.session.add(nuevo_alumno)
                db.session.commit()
                flash('Alumno agregado exitosamente', 'success')
                return redirect(url_for('ver_curso', curso=curso))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al agregar alumno: {str(e)}', 'error')
        else:
            flash('Por favor ingrese el nombre del alumno', 'error')
    
    return render_template('agregar_alumno.html', curso=curso)

@app.route('/agregar_nota/<int:alumno_id>', methods=['GET', 'POST'])
def agregar_nota(alumno_id):
    alumno = Alumno.query.get_or_404(alumno_id)
    
    if request.method == 'POST':
        asignatura = request.form.get('asignatura')
        calificaciones = request.form.get('calificaciones')
        
        if asignatura and calificaciones:
            try:
                notas = [float(x.strip()) for x in calificaciones.split(',') if x.strip()]
                notas_validas = [n for n in notas if 1.0 <= n <= 7.0]
                
                if not notas_validas:
                    flash('Las calificaciones deben estar entre 1.0 y 7.0', 'error')
                else:
                    nota = Nota.query.filter_by(alumno_id=alumno_id, asignatura=asignatura).first()
                    if nota:
                        nota.calificaciones = ','.join(str(n) for n in notas_validas)
                    else:
                        nota = Nota(
                            asignatura=asignatura,
                            calificaciones=','.join(str(n) for n in notas_validas),
                            alumno_id=alumno_id
                        )
                        db.session.add(nota)
                    
                    db.session.commit()
                    flash('Notas guardadas exitosamente', 'success')
                    return redirect(url_for('ver_curso', curso=alumno.curso))
            except ValueError:
                flash('Error en el formato de las calificaciones', 'error')
        else:
            flash('Por favor complete todos los campos', 'error')
    
    return render_template('agregar_nota.html', alumno=alumno, asignaturas=ASIGNATURAS)

@app.route('/exportar_curso_pdf/<curso>')
def exportar_curso_pdf(curso):
    try:
        if curso not in CURSOS:
            flash('Curso no válido', 'error')
            return redirect(url_for('index'))
        
        alumnos = Alumno.query.filter_by(curso=curso)\
                             .order_by(Alumno.nombre_completo)\
                             .all()
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'Informe de Notas - {curso}', 0, 1, 'C')
        pdf.ln(10)
        
        # Encabezados
        pdf.set_font('Arial', 'B', 12)
        headers = ['Alumno'] + ASIGNATURAS + ['Promedio Final']
        col_width = pdf.w / len(headers)
        
        for header in headers:
            pdf.cell(col_width, 7, header, 1, 0, 'C')
        pdf.ln()
        
        # Datos
        pdf.set_font('Arial', '', 10)
        for alumno in alumnos:
            pdf.cell(col_width, 7, alumno.nombre_completo[:25], 1)
            promedios = []
            
            for asignatura in ASIGNATURAS:
                notas = alumno.obtener_promedio_asignatura(asignatura)
                pdf.cell(col_width, 7, f'{notas:.2f}', 1, 0, 'C')
                promedios.append(notas)
            
            promedio_final = sum(promedios) / len(promedios) if promedios else 0
            pdf.cell(col_width, 7, f'{promedio_final:.2f}', 1, 0, 'C')
            pdf.ln()
        
        output_path = os.path.join('static', f'informe_{curso}.pdf')
        pdf.output(output_path, 'F')
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        flash(f'Error al generar el PDF: {str(e)}', 'error')
        return redirect(url_for('ver_curso', curso=curso))

@app.route('/certificado_alumno/<int:alumno_id>')
def certificado_alumno(alumno_id):
    try:
        alumno = Alumno.query.get_or_404(alumno_id)
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'CERTIFICADO DE NOTAS', 0, 1, 'C')
        pdf.ln(10)
        
        # Información del alumno
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Certifico que el alumno(a):', 0, 1)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f'{alumno.nombre_completo}', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Del curso {alumno.curso}, tiene las siguientes calificaciones:', 0, 1)
        pdf.ln(10)
        
        # Tabla de notas
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(80, 7, 'Asignatura', 1)
        pdf.cell(50, 7, 'Calificaciones', 1)
        pdf.cell(50, 7, 'Promedio', 1)
        pdf.ln()
        
        pdf.set_font('Arial', '', 10)
        promedios = []
        for asignatura in ASIGNATURAS:
            notas = [n for n in alumno.notas if n.asignatura == asignatura]
            promedio = alumno.obtener_promedio_asignatura(asignatura)
            promedios.append(promedio)
            
            pdf.cell(80, 7, asignatura, 1)
            if notas:
                pdf.cell(50, 7, notas[0].calificaciones, 1)
            else:
                pdf.cell(50, 7, '-', 1)
            pdf.cell(50, 7, f'{promedio:.1f}', 1)
            pdf.ln()
        
        # Promedio final
        pdf.ln(10)
        promedio_final = sum(promedios) / len(promedios) if promedios else 0
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f'Promedio Final: {promedio_final:.1f}', 0, 1)
        
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
        return redirect(url_for('ver_curso', curso=alumno.curso))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)