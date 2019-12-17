from flask import Blueprint, render_template, session, flash, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from models import *
from flask_login import login_user, login_required, current_user, logout_user
import sys
import sqlalchemy
import json
from datetime import datetime

views_api = Blueprint('views_api',__name__)

@views_api.route('/')
def index():
    return render_template('index.html')

@views_api.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@views_api.route('/crear_monitoreo/<int:id_puente>', methods=['POST'])
def crear_monitoreo(id_puente):
    puente_a_monitorear = Estructura.query.get(id_puente)
    nombre = puente_a_monitorear.nombre.replace(" ","_")
    print(nombre,file=sys.stderr)
    try:
        new_schema = db.engine.execute('CREATE SCHEMA IF NOT EXISTS '+nombre)
    except (Exception) as error:
        print(error)
    finally:
        return redirect(url_for('views_api.informacion_estructura', id=id_puente))


def obtener_nombre_y_activo(id_puente):
    puente = Estructura.query.filter_by(id=id_puente).all()[0]
    nombre_puente = puente.nombre.capitalize()
    tipo_activo = puente.tipo_activo.lower()
    res = {
        'nombre_puente' : nombre_puente,
        'tipo_activo' : tipo_activo
    }
    return res

"""
@views_api.route('/zonas_puente/<int:id_puente>')
def ver_zonas_puente(id_puente):
    lista_zonas = db.session.query(ZonaEstructura,TipoZona).outerjoin(TipoZona, ZonaEstructura.tipo_zona == TipoZona.id).all()
    print(type(lista_zonas),file=sys.stderr)
    results = []
    for i in lista_zonas:
        results.append({'tipo_zona':i[1].nombre_zona,'material':i[0].material}) # Aqui se podrian añadir todas las demas cosas
    print(results,file=sys.stderr)
    context = {'tabla_zonas':results}
    return render_template('listado_zonas.html',**context)
"""

@views_api.route('/login')
def login():
    return render_template('login.html')

@views_api.route('/login', methods=['POST'])
def login_post():
    mail = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False
    user = Usuario.query.filter_by(id=mail).first()
    print(user,file=sys.stderr)
    if not user or not check_password_hash(user.contrasena, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('views_api.login'))
    login_user(user,remember=remember)
    return redirect(url_for('views_api.profile'))

@views_api.route('/signup')
def signup():
    return render_template('signup.html')

@views_api.route('/signup', methods=['POST'])
def signup_post():
    first_name = request.form.get('firstname')
    last_name = request.form.get('lastname')
    mail = request.form.get('mail')
    password = request.form.get('password')
    permisos = request.form.get('permisos')
    print(permisos,file=sys.stderr)
    user = Usuario.query.filter_by(id=mail).first()
    if user:
        flash('Email address already exists')
        return redirect(url_for('views_api.signup'))
    new_user = Usuario(id=mail,nombre=first_name,apellido=last_name,contrasena=generate_password_hash(password),permisos=permisos)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('views_api.login'))

@views_api.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('index.html')

@views_api.route('/estructura/<int:id>')
def informacion_estructura(id):
    estructura = Estructura.query.filter_by(id=id).first()
    estado_monitoreo = EstadoMonitoreo.query.filter_by(id_estructura = id).order_by(EstadoMonitoreo.fecha_estado.desc()).first()
    x = estructura.nombre.lower().replace(" ","_")
    check_schema = db.session.execute("""SELECT * FROM pg_catalog.pg_namespace WHERE nspname = \'"""+x+"""\'""").fetchone()
    esta_monitoreada = True
    if(check_schema is None):
        esta_monitoreada = False
    context = {
        'datos_puente':estructura,
        'estado_monitoreo':estado_monitoreo,
        'esta_monitoreada':esta_monitoreada
    }
    return render_template('tabla_estructura.html', **context)

@views_api.route('/zonas_estructura/<int:id>')
def zonas_de_estructura(id):
    zonas = db.session.query(ZonaEstructura.id, ZonaEstructura.material, TipoZona.nombre_zona).filter(ZonaEstructura.tipo_zona == TipoZona.id, ZonaEstructura.id_estructura==id).all()
    print(zonas, file=sys.stderr)
    context = {
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
        'zonas_puente' : zonas
    }
    return render_template('zonas_puente.html',**context)

@views_api.route('/sensores_estructura/<int:id>')
def sensores_de_estructura(id):
    #FALTA OBTENER DATOS DE DAQ
    sensores_actuales = db.session.query(Sensor.id, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ZonaEstructura.descripcion, InstalacionSensor.fecha_instalacion, SensorInstalado.es_activo).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc()).all()
    print(sensores_actuales, file=sys.stderr)
    context = {
        'id_puente' : id,
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
        'sensores_puente' : sensores_actuales
    }
    return render_template('sensores_puente.html',**context)

@views_api.route('/agregar_sensor/<int:id>')
def agregar_sensor_en(id):
    zonas_puente = db.session.query(ZonaEstructura.id, ZonaEstructura.descripcion).filter_by(id_estructura=id).all()
    x = db.session.query(SensorInstalado.conexion_actual).filter(SensorInstalado.id_estructura == id, SensorInstalado.conexion_actual > 0)
    conexiones = db.session.query(Canal.id.label('x')).except_(x).subquery()
    disponibles = db.session.query(Canal).join(conexiones, conexiones.c.x == Canal.id).order_by(Canal.id_daq.asc(), Canal.numero_canal.asc()).all()
    #print(disponibles)
    tipos_sensores = TipoSensor.query.all()
    session['id_puente'] = id
    context = {
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
        'zonas_puente': zonas_puente,
        'tipos_sensores': tipos_sensores,
        'conexiones' : disponibles
    }
    return render_template('agregar_sensor.html',**context)

@views_api.route('/agregar_sensor',methods=['POST'])
def agregar_sensor_en_post():
    zona_sensor = request.form.get('zona_puente')
    tipo_sensor = request.form.get('tipo_sensor')
    daq_sensor = request.form.get('daqs_disponibles')
    freq_sensor = request.form.get('frecuencia')
    
    nuevo_sensor = Sensor(tipo_sensor=tipo_sensor, frecuencia = freq_sensor)
    nueva_instalacion_sensor = InstalacionSensor(fecha_instalacion=datetime.now())
    db.session.add(nueva_instalacion_sensor)
    db.session.add(nuevo_sensor)
    db.session.flush()
    
    nuevo_sensor_instalado = SensorInstalado(id_instalacion=nueva_instalacion_sensor.id, id_sensor=nuevo_sensor.id, id_zona=zona_sensor, id_estructura=session['id_puente'], conexion_actual=daq_sensor, es_activo=True)
    db.session.add(nuevo_sensor_instalado)
    db.session.flush()
    
    nombre_tipo_sensor = db.session.query(TipoSensor.nombre).filter(TipoSensor.id==tipo_sensor).first().nombre
    nombre_puente = Estructura.query.filter_by(id = session['id_puente']).first().nombre    
    nombre_nueva_tabla = nombre_puente+'.'+nombre_tipo_sensor+'_'+str(session['id_puente'])+str(request.form.get('zona_puente'))+str(nuevo_sensor.id)+str(nuevo_sensor_instalado.id)
    
    db.session.commit()
    x = nombre_nueva_tabla.lower().replace(" ","_")
    crear_tabla_sensor(nuevo_sensor_instalado.id, x)
    return redirect(url_for('views_api.sensores_de_estructura',id=session['id_puente']))

def crear_tabla_sensor(id_sensor_instalado, nombre_nueva_tabla):
    actualizar_nombre_sensor = SensorInstalado.query.filter_by(id=id_sensor_instalado).first()
    actualizar_nombre_sensor.nombre_tabla = nombre_nueva_tabla
    db.session.add(actualizar_nombre_sensor)
    new_table = db.session.execute('CREATE TABLE IF NOT EXISTS '+nombre_nueva_tabla+'(fecha timestamp, lectura double precision, PRIMARY KEY(fecha))')
    new_hypertable = db.session.execute('SELECT create_hypertable(\''+nombre_nueva_tabla+'\', \'fecha\')')
    db.session.commit()

@views_api.route('/lecturas_sensor/<int:sensor>')
def obtener_lecturas(sensor):
    nombre_tabla = SensorInstalado.query.filter_by(id=sensor).first().nombre_tabla
    lecturas = db.session.execute("""SELECT * FROM """+nombre_tabla)
    res = {}
    for i in lecturas:
        res[i['fecha'].strftime("%d-%d-%Y %H:%M:%S.%f")] = i['lectura']
    return res

@views_api.route('/estados_monitoreo/<int:id>')
def historial_monitoreo_estructura(id):
    historial = EstadoMonitoreo.query.filter_by(id_estructura = id).all()
    context = {
        'id_puente' : id,
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
        'estados_monitoreo': historial
    }
    return render_template('historial_monitoreo.html',**context)

@views_api.route('/actualizar_estado/<int:id>')
def actualizar_estado_monitoreo(id):
    context = {
        'id_puente' : id,
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id)
    }
    return render_template('actualizar_estado_monitoreo.html', **context)

@views_api.route('/actualizar_estado/<int:id>',methods=['POST'])
def actualizar_estado_monitoreo_post(id):
    x = EstadoMonitoreo(id_estructura=id, estado = request.form.get('nuevo_estado'), fecha_estado = datetime.now())
    db.session.add(x)
    db.session.commit()
    return redirect(url_for('views_api.historial_monitoreo_estructura',id=id))

@views_api.route('/calibraciones/<int:x>')
def historial_calibraciones_sensor(x):
    sensor = Sensor.query.filter_by(id=x).first()
    tipo_sensor = TipoSensor.query.filter_by(id=sensor.tipo_sensor).first()
    calibraciones = db.session.query(CalibracionSensor.detalles, CalibracionSensor.fecha_calibracion, SensorInstalado.id_sensor, ZonaEstructura.descripcion).filter(CalibracionSensor.id_sensor_instalado == SensorInstalado.id, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.id_sensor == x).order_by(CalibracionSensor.fecha_calibracion.desc()).all()
    context = {
        'id_sensor' : sensor.id,
        'tipo_sensor' : tipo_sensor.nombre,
        'calibraciones' : calibraciones
    }
    return render_template('historial_calibraciones.html',**context)

@views_api.route('/nueva_calibracion/<int:x>')
def nueva_calibracion(x):
    sensor = Sensor.query.filter_by(id=x).first()
    tipo_sensor = TipoSensor.query.filter_by(id=sensor.tipo_sensor).first()
    context = {
        'id_sensor' : sensor.id,
        'tipo_sensor' : tipo_sensor.nombre,
    }
    return render_template('nueva_calibracion.html',**context)

@views_api.route('/nueva_calibracion/<int:x>',methods=['POST'])
def nueva_calibracion_post(x):
    sensor_instalado_actual = db.session.query(SensorInstalado.id).filter(InstalacionSensor.id == SensorInstalado.id_instalacion, SensorInstalado.id_sensor == x).order_by(InstalacionSensor.fecha_instalacion.desc()).first()
    nueva_calibracion = CalibracionSensor(id_sensor_instalado=sensor_instalado_actual.id, fecha_calibracion=datetime.now(), detalles=request.form.get('nueva_calibracion'))
    db.session.add(nueva_calibracion)
    db.session.commit()
    return redirect(url_for('views_api.historial_calibraciones_sensor',x=x))

@views_api.route('/daqs_estructura/<int:id_puente>')
def daqs_de_estructura(id_puente):
    daqs = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas, EstadoDAQ.detalles, EstadoDAQ.fecha_estado).filter(EstadoDAQ.id_daq == DAQ.id, DescripcionDAQ.id_daq == DAQ.id, DAQPorZona.id_daq == DAQ.id, ZonaEstructura.id == DAQPorZona.id_zona, DAQPorZona.id_estructura == id_puente).distinct(DAQ.id).order_by(DAQ.id.asc(), EstadoDAQ.fecha_estado.desc()).all()
    context = {
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
        'daqs' : daqs
    }
    return render_template('daqs_de_estructura.html',**context)

@views_api.route('/daqs_zona/<int:id_zona>')
def daqs_de_zona(id_zona):
    puente = db.session.query(Estructura.nombre, Estructura.tipo_activo).filter(ZonaEstructura.id_estructura == Estructura.id, ZonaEstructura.id == id_zona).first()
    nombre_puente = puente.nombre.capitalize()
    tipo_activo = puente.tipo_activo.lower()
    zona = db.session.query(TipoZona.nombre_zona).filter(ZonaEstructura.tipo_zona == TipoZona.id, ZonaEstructura.id==id_zona).first()
    daqs = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas, EstadoDAQ.detalles, EstadoDAQ.fecha_estado).filter(EstadoDAQ.id_daq == DAQ.id, DescripcionDAQ.id_daq == DAQ.id, DAQPorZona.id_daq == DAQ.id, ZonaEstructura.id == DAQPorZona.id_zona, DAQPorZona.id_zona == id_zona).distinct(DAQ.id).order_by(DAQ.id.asc(), EstadoDAQ.fecha_estado.desc()).all()
    context = {
        'nombre_puente' : nombre_puente,
        'tipo_activo' : tipo_activo,
        'nombre_zona' : zona.nombre_zona,
        'daqs' : daqs
    }
    return render_template('daqs_de_zona.html',**context)

def revisar_disponibilidad_canales(canales, ocupados):
    res = []
    for i in canales:
        if i in (canales and ocupados):
            res.append((i[0], i[1], i[2], True))
        else:
            res.append((i[0], i[1], i[2], False))
    res.sort(key=lambda tup: tup[0])
    return res

@views_api.route('/daq/<int:id_puente>/<int:id_daq>')
def informacion_daq(id_puente, id_daq):
    daq = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas).filter(DescripcionDAQ.id_daq == DAQ.id, DAQ.id==id_daq).first()
    zonas_del_daq = db.session.query(DAQPorZona.id_zona, ZonaEstructura.descripcion).filter(ZonaEstructura.id == DAQPorZona.id_zona, DAQ.id == id_daq).all()
    estado_actual = EstadoDAQ.query.filter_by(id_daq = id_daq).order_by(EstadoDAQ.fecha_estado.desc()).first()
    canales_del_daq = db.session.query(Canal.id, Canal.id_daq, Canal.numero_canal).filter(Canal.id_daq == id_daq).all()
    canales_ocupados = db.session.query(SensorInstalado.conexion_actual, Canal.id_daq, Canal.numero_canal).filter(Canal.id == SensorInstalado.conexion_actual, Canal.id_daq == id_daq, SensorInstalado.conexion_actual > 0)
    x = revisar_disponibilidad_canales(canales_del_daq, canales_ocupados)
    print(x)
    session['id_puente'] = id_puente   
    context = {
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
        'info_daq' : daq,
        'estado_actual':estado_actual,
        'zonas' : zonas_del_daq,
        'canales' : x
    }
    return render_template('informacion_daq.html',**context)

@views_api.route('/historial_daq/<int:id_daq>')
def historial_daq(id_daq):
    x = EstadoDAQ.query.filter_by(id_daq=id_daq).all()
    context = {
        'id_daq' : id_daq,
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente']),
        'estados' : x
    }
    return render_template('historial_daq.html',**context)

@views_api.route('/actualizar_estado_daq/<int:id_daq>')
def actualizar_estado_daq(id_daq):
    context = {
        'id_daq' : id_daq,
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente'])
    }
    return render_template('actualizar_estado_daq.html',**context)

@views_api.route('/actualizar_estado_daq/<int:id_daq>',methods=['POST'])
def actualizar_estado_daq_post(id_daq):
    nuevo_estado = EstadoDAQ(id_daq=id_daq, fecha_estado=datetime.now(), detalles=request.form.get('nuevo_estado'))
    db.session.add(nuevo_estado)
    db.session.commit()
    return redirect(url_for('views_api.historial_daq',id_daq = id_daq))

@views_api.route('/revisiones_daq/<int:id_daq>')
def revisiones_daq(id_daq):
    x = RevisionDAQ.query.filter_by(id_daq=id_daq).all()
    context = {
        'id_daq' : id_daq,
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente']),
        'revisiones' : x
    }
    return render_template('revisiones_daq.html',**context)

@views_api.route('/nueva_revision_daq/<int:id_daq>')
def actualizar_revision_daq(id_daq):
    context = {
        'id_daq' : id_daq,
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente'])
    }
    return render_template('nueva_revision_daq.html',**context)

@views_api.route('/nueva_revision_daq/<int:id_daq>',methods=['POST'])
def actualizar_revision_daq_post(id_daq):
    nueva_revision = RevisionDAQ(id_daq=id_daq, fecha_revision=datetime.now(), detalles=request.form.get('nueva_revision'))
    db.session.add(nueva_revision)
    db.session.commit()
    return redirect(url_for('views_api.revisiones_daq',id_daq = id_daq))
