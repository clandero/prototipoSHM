from flask import Blueprint, render_template, session, flash, request, redirect, url_for, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug import secure_filename
from models import *
from flask_login import login_user, login_required, current_user, logout_user
import sys
import sqlalchemy
from sqlalchemy import or_
import json
import os
from datetime import datetime
import unidecode

views_api = Blueprint('views_api',__name__)

#Función que, dado el id de un puente, obtiene el tipo de activo (Puente, paso nivel, etc..) y nombre (Llacolén, Chacabuco, etc...), y los entrega a las rutas definidas
def obtener_nombre_y_activo(id_puente):
    puente = Estructura.query.filter_by(id=id_puente).all()[0]
    nombre_puente = puente.nombre.capitalize()
    tipo_activo = puente.tipo_activo.lower()
    res = {
        'nombre_puente' : nombre_puente,
        'tipo_activo' : tipo_activo
    }
    return res

#Función que, dado un sensor instalado y un nombre para la nueva tabla, genera la hypertable respectiva
def crear_tabla_sensor(id_sensor_instalado, nombre_nueva_tabla):
    actualizar_nombre_sensor = SensorInstalado.query.filter_by(id=id_sensor_instalado).first()
    actualizar_nombre_sensor.nombre_tabla = nombre_nueva_tabla
    db.session.add(actualizar_nombre_sensor)
    new_table = db.session.execute('CREATE TABLE IF NOT EXISTS '+nombre_nueva_tabla+'(fecha timestamp, lectura double precision, PRIMARY KEY(fecha))')
    new_hypertable = db.session.execute('SELECT create_hypertable(\''+nombre_nueva_tabla+'\', \'fecha\')')
    db.session.commit()

#PERMISOS = TODOS
#Redirige a la vista de Login (si no inicia sesión), o a la vista del mapa (profile.html, si inició sesión)
@views_api.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('views_api.profile'))
    else:
        return render_template('login.html')

#PERMISOS = TODOS
#Requiere login para entrar, muestra todos los puentes en un mapa generado con Leaflet y MarkerCluster (JS)
@views_api.route('/profile')
@login_required
def profile():
    puentes = Estructura.query.all()
    #Genera los markers para el mapa
    markers = []
    for i in puentes:
        markers.append([i.coord_x, i.coord_y, i.tipo_activo.capitalize()+' '+i.nombre.capitalize(), i.id])
    #Variables para el template
    context = {
        'puentes' : puentes,
        'markers' : markers
    }
    return render_template('profile.html', **context)

#PERMISOS = TODOS
#En caso de error, redirige a esta paǵina
@views_api.route('/acceso_restringido')
def usuario_no_autorizado():
    return render_template('usuario_no_autorizado.html')

#PERMISOS = Administrador
#Crea el schema para el monitoreo de un puente, solo el admin. puede usarla
@views_api.route('/crear_monitoreo/<int:id_puente>', methods=['POST'])
@login_required
def crear_monitoreo(id_puente):
    if(current_user.permisos == 'Administrador'):
        puente_a_monitorear = Estructura.query.get(id_puente)
        nombre = puente_a_monitorear.nombre.replace(" ","_")
        try:
            new_schema = db.engine.execute('CREATE SCHEMA IF NOT EXISTS '+nombre)
        except (Exception) as error:
            print(error)
        finally:
            #De no haber errores, redirige a la vista resumen del puente
            return redirect(url_for('views_api.informacion_estructura', id=id_puente))
    else:
        #Si el usuario no está autorizado, redirige a la vista de error
        return redirect(url_for('views_api.usuario_no_autorizado'))

#Maneja el inicio de sesión, con ayuda del package "flask_login"
@views_api.route('/login', methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('views_api.profile'))
    else:
        if(request.method == "GET"):
            return render_template('login.html')
        elif(request.method == "POST"):
            mail = request.form.get('email')
            password = request.form.get('password')
            remember = True if request.form.get('remember') else False
            user = Usuario.query.filter_by(id=mail).first()
            if not user or not check_password_hash(user.contrasena, password):
                flash('Please check your login details and try again.')
                return redirect(url_for('views_api.login'))
            login_user(user,remember=remember)
            return redirect(url_for('views_api.profile'))
        else:
            return redirect(url_for('views_api.usuario_no_autorizado'))

#Crea nuevos usuarios en la plataforma, requiere de correo (primary_key), nombre, apellido y permisos
@views_api.route('/signup')
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('views_api.usuario_no_autorizado'))
    else:
        if(request.method == "GET"):
            return render_template('signup.html')
        elif(request.method == "POST"):
            first_name = request.form.get('firstname')
            last_name = request.form.get('lastname')
            mail = request.form.get('mail')
            password = request.form.get('password')
            permisos = request.form.get('permisos')
            user = Usuario.query.filter_by(id=mail).first()
            if user:
                flash('Email address already exists')
                return redirect(url_for('views_api.signup'))
            new_user = Usuario(id=mail,nombre=first_name,apellido=last_name,contrasena=generate_password_hash(password),permisos=permisos)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('views_api.login'))

#Cerrar sesión
@views_api.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('login.html')

#PERMISOS = TODOS
#Muestra el detalle de una estructura, dado el id del puente en la BD
@views_api.route('/estructura/<int:id>')
@login_required
def informacion_estructura(id):
    #Detalles generales de la estructura
    estructura = Estructura.query.filter_by(id=id).first()
    estado_monitoreo = EstadoMonitoreo.query.filter_by(id_estructura = id).order_by(EstadoMonitoreo.fecha_estado.desc()).first()
    #Revisa si el schema del puente existe, de no ser así, es por que no está siendo monitoreada
    nombre_del_schema = estructura.nombre.lower().replace(" ","_")
    check_schema = db.session.execute("""SELECT * FROM pg_catalog.pg_namespace WHERE nspname = \'"""+nombre_del_schema+"""\'""").fetchone()
    esta_monitoreada = True
    if(check_schema is None):
        esta_monitoreada = False
    #Consulta por rutas de imágenes y BIM asociados
    imagenes_estructura = ImagenEstructura.query.filter_by(id_estructura = id).all()
    bim_estructura = VisualizacionBIM.query.filter_by(id_estructura = id).first()
    context = {
        'datos_puente':estructura,
        'estado_monitoreo':estado_monitoreo,
        'esta_monitoreada':esta_monitoreada,
        'imagenes_estructura':imagenes_estructura,
        'bim_estructura' : bim_estructura
    }
    return render_template('tabla_estructura.html', **context)

#PERMISOS = TODOS
#Muestra el detalle de las zonas en una estructura
@views_api.route('/zonas_estructura/<int:id>')
@login_required
def zonas_de_estructura(id):
    zonas = db.session.query(ZonaEstructura.id, ZonaEstructura.descripcion, ZonaEstructura.material, TipoZona.nombre_zona).filter(ZonaEstructura.tipo_zona == TipoZona.id, ZonaEstructura.id_estructura==id).all()
    context = {
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
        'zonas_puente' : zonas
    }
    return render_template('zonas_puente.html',**context)

#PERMISOS = TODOS
#Obtiene el detalle de los sensores instalados actualmente
@views_api.route('/sensores_estructura/<int:id>')
@login_required
def sensores_de_estructura(id):
    sensores_actuales = db.session.query(Sensor.id, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ZonaEstructura.descripcion, InstalacionSensor.fecha_instalacion, SensorInstalado.es_activo).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc()).all()
    context = {
        'id_puente' : id,
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
        'sensores_puente' : sensores_actuales
    }
    return render_template('sensores_puente.html',**context)

#PERMISOS = Administrador, dueño
#Método que permite instalar un nuevo sensor en una estructura
@views_api.route('/agregar_sensor/<int:id>', methods=["GET", "POST"])
@login_required
def agregar_sensor_en(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Dueño'):
        #En GET se carga el formulario que permite agregar nuevos sensores a la estructura
        if(request.method == "GET"):
            zonas_puente = db.session.query(ZonaEstructura.id, ZonaEstructura.descripcion).filter_by(id_estructura=id).all()
            #Se filtran los sensores ya conectados
            sensores_conectados = db.session.query(SensorInstalado.conexion_actual).filter(SensorInstalado.id_estructura == id, SensorInstalado.conexion_actual > 0)
            conexiones = db.session.query(Canal.id.label('sensores_conectados')).except_(sensores_conectados).subquery()
            #Se obtienen las conexiones disponibles de los DAQs
            disponibles = db.session.query(Canal).join(conexiones, conexiones.c.sensores_conectados == Canal.id).order_by(Canal.id_daq.asc(), Canal.numero_canal.asc()).all()
            tipos_sensores = TipoSensor.query.all()
            #Se guarda momentaneamente el id del puente en la sesión actual
            session['id_puente'] = id
            context = {
                'id_puente' : id,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
                'zonas_puente': zonas_puente,
                'tipos_sensores': tipos_sensores,
                'conexiones' : disponibles
            }
            return render_template('agregar_sensor.html',**context)
        #En POST se envia lo ingresado via formulario, para guardar en la BD
        elif(request.method == "POST"):
            zona_sensor = request.form.get('zona_puente')
            tipo_sensor = request.form.get('tipo_sensor')
            daq_sensor = request.form.get('daqs_disponibles')
            freq_sensor = request.form.get('frecuencia')
            #Se guarda el nuevo sensor instalado, y la fecha de la instalación en la BD
            try:
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
            #En caso de ocurrir un fallo, se hace un rollback()
            except:
                db.session.rollback()
                raise
            #Finalmente, se redirige al listado de sensores disponibles
            finally:
                return redirect(url_for('views_api.sensores_de_estructura',id=session['id_puente']))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))


#PERMISOS = Administrador, dueño y analista
#API que obtiene las lecturas de un sensor en el formato JSON
@views_api.route('/lecturas_sensor/<int:sensor>/<int:periodo>')
def obtener_lecturas_rango(sensor, periodo):
    try:
        nombre_tabla = SensorInstalado.query.filter_by(id=sensor).first().nombre_tabla
        rango_de_tiempo = ""
        if(periodo == 1):
            rango_de_tiempo = "12 seconds"
        elif(periodo == 2):
            rango_de_tiempo = "288 seconds"
        elif(periodo == 3):
            rango_de_tiempo = "2016 seconds"
        lecturas = db.session.execute("""SELECT time_bucket('"""+rango_de_tiempo+"""', x.fecha) as sec, max(lectura),min(lectura),avg(lectura) FROM """+nombre_tabla+""" as x GROUP BY sec ORDER BY sec DESC LIMIT 300""")
        res = {}
        for i in lecturas:
            #res[i['fecha'].strftime("%d-%d-%Y %H:%M:%S.%f")] = i['lectura']
            res[i['sec'].strftime("%d-%d-%Y %H:%M:%S.%f")] = {
                'max' : i['max'],
                'min' : i['min'],
                'avg' : i['avg']
            }
        return res
    except Exception as e:
        return render_template('usuario_no_autorizado.html')

#PERMISOS = Administrador, dueño y analista
#API que obtiene las lecturas de un sensor en el formato JSON
@views_api.route('/lecturas_sensor/<int:sensor>')
def obtener_lecturas(sensor):
    try:
        nombre_tabla = SensorInstalado.query.filter_by(id=sensor).first().nombre_tabla
        lecturas = db.session.execute("""SELECT time_bucket('10 seconds', x.fecha) as sec, max(lectura),min(lectura),avg(lectura) FROM """+nombre_tabla+""" as x GROUP BY sec ORDER BY sec DESC LIMIT 300""")
        res = {}
        for i in lecturas:
            #res[i['fecha'].strftime("%d-%d-%Y %H:%M:%S.%f")] = i['lectura']
            res[i['sec'].strftime("%d-%d-%Y %H:%M:%S.%f")] = {
                'max' : i['max'],
                'min' : i['min'],
                'avg' : i['avg']
            }
        return res
    except Exception as e:
        return render_template('usuario_no_autorizado.html')

#PERMISOS = TODOS
#Función que permite a la barra de búsqueda encontrar el listado de estructuras
@views_api.route('/buscar_estructura', methods=['POST'])
@login_required
def buscar_estructura():
    try:
        x = request.form.get('autocomplete').split()[0]
        return redirect(url_for('views_api.informacion_estructura', id=x))
    except Exception as e:
        return render_template('estructura_no_existe.html')

#PERMISOS = Administrador, analista
#Función que permite obtener el historial de estado de monitoreo de una estructura
@views_api.route('/estados_monitoreo/<int:id>')
@login_required
def historial_monitoreo_estructura(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        historial = EstadoMonitoreo.query.filter_by(id_estructura = id).all()
        context = {
            'id_puente' : id,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
            'estados_monitoreo': historial
        }
        return render_template('historial_monitoreo.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/actualizar_estado/<int:id>', methods=["GET","POST"])
@login_required
def actualizar_estado_monitoreo(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == "GET"):
            context = {
                'id_puente' : id,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id)
            }
            return render_template('actualizar_estado_monitoreo.html', **context)
        elif(request.method == "POST"):
            x = EstadoMonitoreo(id_estructura=id, estado = request.form.get('nuevo_estado'), fecha_estado = datetime.now())
            db.session.add(x)
            db.session.commit()
            return redirect(url_for('views_api.historial_monitoreo_estructura',id=id))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/calibraciones/<int:x>')
@login_required
def historial_calibraciones_sensor(x):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        sensor = Sensor.query.filter_by(id=x).first()
        tipo_sensor = TipoSensor.query.filter_by(id=sensor.tipo_sensor).first()
        calibraciones = db.session.query(CalibracionSensor.detalles, CalibracionSensor.fecha_calibracion, SensorInstalado.id_sensor, ZonaEstructura.descripcion).filter(CalibracionSensor.id_sensor_instalado == SensorInstalado.id, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.id_sensor == x).order_by(CalibracionSensor.fecha_calibracion.desc()).all()
        context = {
            'id_sensor' : sensor.id,
            'tipo_sensor' : tipo_sensor.nombre,
            'calibraciones' : calibraciones
        }
        return render_template('historial_calibraciones.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/nueva_calibracion/<int:x>', methods=["GET","POST"])
@login_required
def nueva_calibracion(x):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == "GET"):
            sensor = Sensor.query.filter_by(id=x).first()
            tipo_sensor = TipoSensor.query.filter_by(id=sensor.tipo_sensor).first()
            context = {
                'id_sensor' : sensor.id,
                'tipo_sensor' : tipo_sensor.nombre,
            }
            return render_template('nueva_calibracion.html',**context)
        elif(request.method == "POST"):
            sensor_instalado_actual = db.session.query(SensorInstalado.id).filter(InstalacionSensor.id == SensorInstalado.id_instalacion, SensorInstalado.id_sensor == x).order_by(InstalacionSensor.fecha_instalacion.desc()).first()
            nueva_calibracion = CalibracionSensor(id_sensor_instalado=sensor_instalado_actual.id, fecha_calibracion=datetime.now(), detalles=request.form.get('nueva_calibracion'))
            db.session.add(nueva_calibracion)
            db.session.commit()
            return redirect(url_for('views_api.historial_calibraciones_sensor',x=x))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/daqs_estructura/<int:id_puente>')
@login_required
def daqs_de_estructura(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        daqs = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas, EstadoDAQ.detalles, EstadoDAQ.fecha_estado).filter(EstadoDAQ.id_daq == DAQ.id, DescripcionDAQ.id_daq == DAQ.id, DAQPorZona.id_daq == DAQ.id, ZonaEstructura.id == DAQPorZona.id_zona, DAQPorZona.id_estructura == id_puente).distinct(DAQ.id).order_by(DAQ.id.asc(), EstadoDAQ.fecha_estado.desc()).all()
        context = {
            'id_puente' : id_puente,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
            'daqs' : daqs
        }
        return render_template('daqs_de_estructura.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/daqs_zona/<int:id_zona>')
@login_required
def daqs_de_zona(id_zona):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        puente = db.session.query(Estructura.id, Estructura.nombre, Estructura.tipo_activo).filter(ZonaEstructura.id_estructura == Estructura.id, ZonaEstructura.id == id_zona).first()
        nombre_puente = puente.nombre.capitalize()
        tipo_activo = puente.tipo_activo.lower()
        zona = db.session.query(TipoZona.nombre_zona).filter(ZonaEstructura.tipo_zona == TipoZona.id, ZonaEstructura.id==id_zona).first()
        daqs = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas, EstadoDAQ.detalles, EstadoDAQ.fecha_estado).filter(EstadoDAQ.id_daq == DAQ.id, DescripcionDAQ.id_daq == DAQ.id, DAQPorZona.id_daq == DAQ.id, ZonaEstructura.id == DAQPorZona.id_zona, DAQPorZona.id_zona == id_zona).distinct(DAQ.id).order_by(DAQ.id.asc(), EstadoDAQ.fecha_estado.desc()).all()
        context = {
            'id_puente' : puente.id,
            'nombre_puente' : nombre_puente,
            'tipo_activo' : tipo_activo,
            'nombre_zona' : zona.nombre_zona,
            'daqs' : daqs
        }
        return render_template('daqs_de_zona.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

def revisar_disponibilidad_canales(canales, ocupados):
    res = []
    for i in canales:
        if i in (canales and ocupados):
            res.append((i[0], i[1], i[2], True))
        else:
            res.append((i[0], i[1], i[2], False))
    res.sort(key=lambda tup: tup[0])
    return res

#PERMISOS = Administrador, analista
@views_api.route('/daq/<int:id_puente>/<int:id_daq>')
@login_required
def informacion_daq(id_puente, id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
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
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/historial_daq/<int:id_daq>')
@login_required
def historial_daq(id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        x = EstadoDAQ.query.filter_by(id_daq=id_daq).all()
        context = {
            'id_daq' : id_daq,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente']),
            'estados' : x
        }
        return render_template('historial_daq.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/actualizar_estado_daq/<int:id_daq>', methods=["GET","POST"])
@login_required
def actualizar_estado_daq(id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == "GET"):
            context = {
                'id_daq' : id_daq,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente'])
            }
            return render_template('actualizar_estado_daq.html',**context)
        elif(request.method == "POST"):
            nuevo_estado = EstadoDAQ(id_daq=id_daq, fecha_estado=datetime.now(), detalles=request.form.get('nuevo_estado'))
            db.session.add(nuevo_estado)
            db.session.commit()
            return redirect(url_for('views_api.historial_daq',id_daq = id_daq))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/revisiones_daq/<int:id_daq>')
@login_required
def revisiones_daq(id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        x = RevisionDAQ.query.filter_by(id_daq=id_daq).all()
        context = {
            'id_daq' : id_daq,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente']),
            'revisiones' : x
        }
        return render_template('revisiones_daq.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/nueva_revision_daq/<int:id_daq>', methods=["GET","POST"])
@login_required
def actualizar_revision_daq(id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == "GET"):
            context = {
                'id_daq' : id_daq,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente'])
            }
            return render_template('nueva_revision_daq.html',**context)
        elif(request.method == "POST"):
            nueva_revision = RevisionDAQ(id_daq=id_daq, fecha_revision=datetime.now(), detalles=request.form.get('nueva_revision'))
            db.session.add(nueva_revision)
            db.session.commit()
            return redirect(url_for('views_api.revisiones_daq',id_daq = id_daq))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/clusters/<int:id_puente>')
@login_required
def clusters_estructura(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        clusters = db.session.query(Conjunto.id, Conjunto.nombre).filter(ConjuntoZona.id_conjunto == Conjunto.id, ConjuntoZona.id_estructura == id_puente).all()
        context = {
            'id_puente' : id_puente,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
            'clusters' : clusters
        }
        return render_template('clusters_estructura.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/sensores_cluster/<int:id_cluster>')
@login_required
def sensores_cluster(id_cluster):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        nombre_cluster = db.session.query(Conjunto.nombre).filter_by(id = id_cluster).first().nombre
        sensores_cluster = db.session.query(Sensor.id, SensorInstalado.id.label("si"), ZonaEstructura.descripcion, Sensor.frecuencia, TipoSensor.nombre, SensorInstalado.es_activo).filter(SensorInstalado.id == ConjuntoSensorInstalado.id_sensor_instalado, Sensor.id == SensorInstalado.id_sensor, ZonaEstructura.id == SensorInstalado.id_zona, TipoSensor.id == Sensor.tipo_sensor, ConjuntoSensorInstalado.id_conjunto == id_cluster).all()
        print(sensores_cluster)
        context = {
            'id_cluster' : id_cluster,
            'nombre_cluster' : nombre_cluster,
            'sensores_cluster' : sensores_cluster
        }
        return render_template('sensores_cluster.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/nuevo_sensor_cluster/<int:id_cluster>')
@login_required
def agregar_sensor_cluster(id_cluster):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == "GET"):
            sensores_ocupados = db.session.query(SensorInstalado.id, TipoSensor.nombre, ZonaEstructura.descripcion).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.es_activo == True, ConjuntoSensorInstalado.id_sensor_instalado == SensorInstalado.id, ConjuntoSensorInstalado.id_conjunto == id_cluster)
            sensores_disponibles = db.session.query(SensorInstalado.id, TipoSensor.nombre, ZonaEstructura.descripcion).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.es_activo == True).except_(sensores_ocupados).all()
            context = {
                'id_cluster' : id_cluster,
                'sensores' : sensores_disponibles
            }
            return render_template('agregar_sensor_cluster.html',**context)
        elif(request.method == "POST"):
            id_sensor = request.form.get('sensor')
            zona = db.session.query(SensorInstalado.id_estructura, SensorInstalado.id_zona).filter(SensorInstalado.id == id_sensor).first()
            nuevo_sensor_cluster = ConjuntoSensorInstalado(id_sensor_instalado = id_sensor, id_conjunto = id_cluster)
            db.session.add(nuevo_sensor_cluster)
            check_if_exists = ConjuntoZona.query.filter(ConjuntoZona.id_conjunto == id_cluster, ConjuntoZona.id_zona == zona.id_zona, ConjuntoZona.id_estructura == zona.id_estructura).first()
            if(check_if_exists is None):
                nueva_zona_cluster = ConjuntoZona(id_conjunto = id_cluster, id_zona = zona.id_zona, id_estructura = zona.id_estructura)
                db.session.add(nueva_zona_cluster)
            db.session.commit()
            return redirect(url_for('views_api.sensores_cluster', id_cluster = id_cluster))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/sensores_zona/<int:id_zona>')
@login_required
def sensores_por_zona(id_zona):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        puente = db.session.query(Estructura.nombre, Estructura.tipo_activo).filter(ZonaEstructura.id_estructura == Estructura.id, ZonaEstructura.id == id_zona).first()
        nombre_puente = puente.nombre.capitalize()
        tipo_activo = puente.tipo_activo.lower()
        zona = db.session.query(ZonaEstructura.descripcion).filter(ZonaEstructura.id==id_zona).first()
        sensores = db.session.query(Sensor.id, SensorInstalado.id.label('si'), Sensor.frecuencia, TipoSensor.nombre).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_zona == id_zona).all()
        context = {
            'nombre_puente' : nombre_puente,
            'tipo_activo' : tipo_activo,
            'nombre_zona' : zona.descripcion,
            'sensores' : sensores
        }
        return render_template('sensores_por_zona.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/historial_sensor/<int:id_sensor>')
@login_required
def historial_estado_sensor(id_sensor):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        x = db.session.query(SensorInstalado.id_estructura).filter(SensorInstalado.id_sensor == id_sensor).first().id_estructura
        tipo_sensor = db.session.query(TipoSensor.nombre).filter(TipoSensor.id == Sensor.tipo_sensor, Sensor.id == id_sensor).first().nombre
        historial = db.session.query(SensorInstalado.id, ZonaEstructura.descripcion, EstadoSensor.detalles, EstadoSensor.fecha_estado).filter(SensorInstalado.id == EstadoSensor.id_sensor_instalado, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.id_sensor == id_sensor).all()
        context = {
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(x),
            'tipo_sensor': tipo_sensor,
            'id_sensor': id_sensor,
            'historial' : historial
        }
        return render_template('historial_sensor.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/actualizar_estado_sensor/<int:id_sensor>')
@login_required
def actualizar_estado_sensor(id_sensor):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == "GET"):
            x = db.session.query(SensorInstalado.id_estructura).filter(SensorInstalado.id_sensor == id_sensor).first().id_estructura
            tipo_sensor = db.session.query(TipoSensor.nombre).filter(TipoSensor.id == Sensor.tipo_sensor, Sensor.id == id_sensor).first().nombre
            context = {
                'id_sensor' : id_sensor,
                'tipo_sensor' : tipo_sensor,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(x)
            }
            return render_template('actualizar_estado_sensor.html', **context)
        elif(request.method == "POST"):
            id_sensor_instalado_actual = db.session.query(SensorInstalado.id, InstalacionSensor.fecha_instalacion).filter(InstalacionSensor.id == SensorInstalado.id_instalacion, SensorInstalado.id_sensor == id_sensor).order_by(InstalacionSensor.fecha_instalacion.desc()).first().id
            x = EstadoSensor(id_sensor_instalado=id_sensor_instalado_actual, detalles = request.form.get('nuevo_estado'), fecha_estado = datetime.now())
            db.session.add(x)
            db.session.commit()
            return redirect(url_for('views_api.historial_estado_sensor',id_sensor=id_sensor))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/grupo_definido_usuario', methods=['GET','POST'])
@login_required
def grupo_definido_usuario():
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == 'GET'):
            sensores = db.session.query(SensorInstalado.id, SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion, TipoSensor.nombre.label('tipo_sensor'), Estructura.nombre, Estructura.tipo_activo, ZonaEstructura.descripcion, SensorInstalado.es_activo, SensorInstalado.nombre_tabla, SensorInstalado.conexion_actual).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, InstalacionSensor.id == SensorInstalado.id_instalacion, Estructura.id == SensorInstalado.id_estructura, ZonaEstructura.id == SensorInstalado.id_zona).distinct(SensorInstalado.id_sensor).order_by(SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion.desc()).all()
            context = {
                'sensores' : sensores
            }
            return render_template('grupo_definido_usuario.html',**context)
        elif(request.method == 'POST'):
            nombre = request.form.get('nombre_grupo')
            sensores = request.form.getlist('sensores_elegidos')
            nuevo_grupo = GrupoDefinidoUsuario(nombre=nombre, id_usuario=current_user.id, fecha_creacion=datetime.now())
            db.session.add(nuevo_grupo)
            db.session.flush()
            for i in sensores:
                x = SensorPorGrupoDefinido(id_sensor_instalado=i, id_grupo=nuevo_grupo.id, fecha_creacion=datetime.now())
                db.session.add(x)
            db.session.commit()
            return redirect(url_for('views_api.grupos_usuario'))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/grupos_usuario')
@login_required
def grupos_usuario():
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        grupos = GrupoDefinidoUsuario.query.filter_by(id_usuario = current_user.id).all()
        context = {
            'grupos' : grupos
        }
        return render_template('listado_grupos.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/sensores_de_grupo/<int:id>')
@login_required
def sensores_de_grupo(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        sensores = db.session.query(TipoSensor.nombre.label('tipo_sensor'), ZonaEstructura.descripcion, Estructura.tipo_activo, Estructura.nombre, SensorInstalado.id, SensorInstalado.id_sensor, SensorInstalado.nombre_tabla, SensorPorGrupoDefinido.fecha_creacion).filter(GrupoDefinidoUsuario.id == SensorPorGrupoDefinido.id_grupo, SensorInstalado.id == SensorPorGrupoDefinido.id_sensor_instalado, Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, ZonaEstructura.id == SensorInstalado.id_zona, Estructura.id == SensorInstalado.id_estructura, GrupoDefinidoUsuario.id == id).all()
        print(sensores)
        nombre_grupo = db.session.query(GrupoDefinidoUsuario.nombre).filter(GrupoDefinidoUsuario.id == id).first().nombre
        context = {
            'nombre_grupo':nombre_grupo,
            'sensores':sensores
        }
        return render_template('sensores_de_grupo.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/eliminar_grupo/<int:id>', methods=['POST'])
@login_required
def eliminar_grupo(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        sensores_a_eliminar = SensorPorGrupoDefinido.query.filter_by(id_grupo = id).delete()
        grupo_a_eliminar = GrupoDefinidoUsuario.query.filter_by(id = id).delete()
        db.session.commit()
        return redirect(url_for('views_api.grupos_usuario'))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
@views_api.route('/editar_grupo/<int:id>', methods=['GET','POST'])
@login_required
def editar_grupo(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == 'GET'):
            sensores_del_grupo = db.session.query(SensorInstalado.id, SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion, TipoSensor.nombre.label('tipo_sensor'), Estructura.nombre, Estructura.tipo_activo, ZonaEstructura.descripcion, SensorInstalado.es_activo, SensorInstalado.nombre_tabla, SensorInstalado.conexion_actual).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, InstalacionSensor.id == SensorInstalado.id_instalacion, Estructura.id == SensorInstalado.id_estructura, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.id == SensorPorGrupoDefinido.id_sensor_instalado, SensorPorGrupoDefinido.id_grupo == GrupoDefinidoUsuario.id, GrupoDefinidoUsuario.id == id).distinct(SensorInstalado.id_sensor).order_by(SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion.desc()).all()
            sensores_disponibles = sensores = db.session.query(SensorInstalado.id, SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion, TipoSensor.nombre.label('tipo_sensor'), Estructura.nombre, Estructura.tipo_activo, ZonaEstructura.descripcion, SensorInstalado.es_activo, SensorInstalado.nombre_tabla, SensorInstalado.conexion_actual).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, InstalacionSensor.id == SensorInstalado.id_instalacion, Estructura.id == SensorInstalado.id_estructura, ZonaEstructura.id == SensorInstalado.id_zona).distinct(SensorInstalado.id_sensor).order_by(SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion.desc()).all()
            nombre_grupo = db.session.query(GrupoDefinidoUsuario.nombre).filter_by(id = id).first().nombre
            print(nombre_grupo)
            context = {
                'id_grupo' : id,
                'nombre_grupo' : nombre_grupo, 
                'sensores_disponibles' : sensores_disponibles,
                'sensores_del_grupo' : sensores_del_grupo
            }
            return render_template('actualizar_grupo_definido_usuario.html',**context)
        elif(request.method == 'POST'):
            inicial_query = SensorPorGrupoDefinido.query.filter_by(id_grupo = id).all()
            inicial_lista = [(i.id_sensor_instalado, i.id_grupo) for i in inicial_query] 
            final_query = request.form.getlist('sensores_elegidos')
            final_lista = [(int(i), id) for i in final_query]
            #remover elementos
            for i in inicial_lista:
                if i not in final_lista:
                    #print(str(i)+' removido')
                    x = SensorPorGrupoDefinido.query.filter_by(id_sensor_instalado = i[0], id_grupo=i[1]).delete()
            #añadir elementos
            for i in final_lista:
                if i not in inicial_lista:
                    #print(str(i)+' añadido')
                    y = SensorPorGrupoDefinido(id_sensor_instalado = i[0], id_grupo = i[1], fecha_creacion = datetime.now())
                    db.session.add(y)
            db.session.commit()
            return redirect(url_for('views_api.grupos_usuario'))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
@views_api.route('/informes_estructura/<int:id_puente>')
@login_required
def informes_monitoreo_estructura(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        print(os.getcwd(), file=sys.stderr)
        informes = db.session.query(InformeMonitoreoVisual.ruta_acceso_archivo, InformeMonitoreoVisual.id_informe, Usuario.nombre, Usuario.apellido, InformeMonitoreoVisual.contenido, InformeMonitoreoVisual.fecha).filter(InformeMonitoreoVisual.id_usuario == Usuario.id, InformeMonitoreoVisual.id_estructura == id_puente).all()
        context = {
            'id_puente' : id_puente,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
            'informes' : informes
        }
        return render_template('informes_monitoreo_estructura.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
@views_api.route('/informe/<int:id>')
@login_required
def ver_informe(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        informe = InformeMonitoreoVisual.query.filter_by(id_informe = id).first()
        print(informe.ruta_acceso_archivo)
        context = {
            'informe' : informe
        }
        return render_template('pdf_informe.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))


#PERMISOS = Administrador, analista, Dueño
@views_api.route('/eliminar_informe/<int:id>', methods=['POST'])
@login_required
def eliminar_informe(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        informe = InformeMonitoreoVisual.query.filter_by(id_informe = id).first()
        os.chdir('static/reports')
        os.remove(informe.ruta_acceso_archivo)
        os.chdir('../..')
        informe_a_borrar = InformeMonitoreoVisual.query.filter_by(id_informe = id).delete()
        db.session.commit()
        return redirect(url_for('views_api.informes_monitoreo_estructura',id_puente=informe.id_estructura))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))


#PERMISOS = Administrador, analista, Dueño
@views_api.route('/agregar_informe/<int:id_puente>', methods=['POST'])
@login_required
def agregar_informe(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        print(os.getcwd())
        file = request.files['input-file-now']
        os.chdir('static/reports')
        file.save(secure_filename(unidecode.unidecode(file.filename.replace(" ","_"))))
        os.chdir('../..')
        nuevo_informe = InformeMonitoreoVisual(id_usuario=current_user.id, id_estructura=id_puente, contenido=request.form.get('contenido'), fecha=datetime.now(), ruta_acceso_archivo=unidecode.unidecode(file.filename.replace(" ","_")))
        db.session.add(nuevo_informe)
        db.session.commit()
        return redirect(url_for('views_api.informes_monitoreo_estructura', id_puente=id_puente))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
@views_api.route('/agregar_informe', methods=['POST'])
@login_required
def agregar_informe_test():
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        print(os.getcwd())
        id_puente = request.form.get('id_puente')
        file = request.files['input-file-now']
        os.chdir('static/reports')
        file.save(secure_filename(unidecode.unidecode(file.filename.replace(" ","_"))))
        os.chdir('../..')
        nuevo_informe = InformeMonitoreoVisual(id_usuario=current_user.id, id_estructura=id_puente, contenido=request.form.get('contenido'), fecha=datetime.now(), ruta_acceso_archivo=unidecode.unidecode(file.filename.replace(" ","_")))
        db.session.add(nuevo_informe)
        db.session.commit()
        return redirect(url_for('views_api.informes_monitoreo_estructura', id_puente=id_puente))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
@views_api.route('/mis_informes')
@login_required
def informes_monitoreo_usuario():
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        informes = db.session.query(InformeMonitoreoVisual.ruta_acceso_archivo, InformeMonitoreoVisual.id_informe, Usuario.nombre, Usuario.apellido, InformeMonitoreoVisual.contenido, InformeMonitoreoVisual.fecha).filter(InformeMonitoreoVisual.id_usuario == Usuario.id, InformeMonitoreoVisual.id_usuario == current_user.id).all()
        context = {
            'informes' : informes
        }
        return render_template('mis_informes_monitoreo.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
@views_api.route('/informes_zona/<int:id_zona>')
@login_required
def informes_monitoreo_zona(id_zona):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        estructura = db.session.query(ZonaEstructura.id_estructura, ZonaEstructura.descripcion).filter(ZonaEstructura.id == id_zona).first()
        id_estructura = estructura.id_estructura
        descripcion = estructura.descripcion
        informes = db.session.query(Usuario.nombre, Usuario.apellido, InformeMonitoreoVisual.id_informe, InformeMonitoreoVisual.id_usuario, InformeMonitoreoVisual.contenido, InformeMonitoreoVisual.fecha, InformeMonitoreoVisual.ruta_acceso_archivo, InformeZona.id_zona).filter(Usuario.id == InformeMonitoreoVisual.id_usuario, InformeZona.id_informe == InformeMonitoreoVisual.id_informe, InformeZona.id_zona == id_zona).all()
        context = {
            'id_puente' : id_estructura,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_estructura),
            'descripcion' : descripcion,
            'informes' : informes
        }
        return render_template('informes_monitoreo_zona.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
@views_api.route('/hallazgos_informe/<int:id_informe>')
@login_required
def hallazgos_de_informe(id_informe):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        hallazgos = db.session.query(HallazgoVisual.id, HallazgoVisual.detalle_hallazgo, HallazgoVisual.fecha, HallazgoVisual.id_zona, ZonaEstructura.descripcion, HallazgoVisual.id_estructura, HallazgoInforme.id_informe).filter(HallazgoVisual.id == HallazgoInforme.id_hallazgo, ZonaEstructura.id == HallazgoVisual.id_zona, HallazgoInforme.id_informe == id_informe).all()
        res = []
        for i in hallazgos:
            audiovisual = MaterialAudiovisual.query.filter_by(id_hallazgo = i[0]).all()
            element = {
                'hallazgo' : i,
                'material_apoyo' : audiovisual
            }
            res.append(element)
        context = {
            'id_informe' : id_informe,
            'hallazgos' : res
        }
        return render_template('hallazgos_de_informe.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
@views_api.route('/agregar_hallazgo/<int:id_informe>', methods=['GET','POST'])
@login_required
def agregar_hallazgo(id_informe):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        if(request.method == 'GET'):
            id_estructura = InformeMonitoreoVisual.query.filter_by(id_informe = id_informe).first().id_estructura
            zonas_estructura = ZonaEstructura.query.filter_by(id_estructura = id_estructura).all()
            context = {
                'zonas_puente' : zonas_estructura,
                'id_estructura' : id_estructura,
                'id_informe' : id_informe
            }
            return render_template('agregar_hallazgo.html',**context)
        elif(request.method == 'POST'):
            id_estructura = InformeMonitoreoVisual.query.filter_by(id_informe = id_informe).first().id_estructura
            nuevo_hallazgo = HallazgoVisual(id_usuario=current_user.id, detalle_hallazgo=request.form.get('detalle'), fecha=datetime.now(), id_zona = request.form.get('zona_puente'), id_estructura=id_estructura)
            db.session.add(nuevo_hallazgo)
            db.session.flush()
            imagenes = request.files.getlist('imagenes')
            list_img = []
            os.chdir('static/images')
            for i in imagenes:
                print(i)
                i.save(secure_filename(unidecode.unidecode(i.filename.replace(" ","_"))))
                list_img.append(MaterialAudiovisual(id_hallazgo=nuevo_hallazgo.id, tipo_material='imagen',ruta_acceso_archivo=unidecode.unidecode(i.filename.replace(" ","_"))))
            os.chdir('../..')
            db.session.bulk_save_objects(list_img)
            asociar_a_informe = HallazgoInforme(id_informe=id_informe, id_hallazgo=nuevo_hallazgo.id)
            db.session.add(asociar_a_informe)
            db.session.commit()
            return redirect(url_for('views_api.hallazgos_de_informe',id_informe=id_informe))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

@views_api.route('/static/bim/<string:filename>')
def show_3d_bim(filename):
    return send_file('./static/bim/'+filename)

@views_api.route('/static/images/<string:filename>')
def show_image(filename):
    return send_file('./static/images/'+filename)

@views_api.route('/static/reports/<string:filename>')
def show_report(filename):
    return send_file('./static/reports/'+filename)

#PERMISOS = Administrador, analista
@views_api.route('/agregar_daq/<int:id_puente>', methods = ['GET','POST'])
@login_required
def agregar_daq(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == 'GET'):
            zonas_puente = ZonaEstructura.query.filter_by(id_estructura = id_puente).all()
            context = {
                'id_puente' : id_puente,
                'zonas_puente' : zonas_puente,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente)
            }
            return render_template('agregar_daq.html',**context)
        elif(request.method == 'POST'):
            nuevo_daq = DAQ(nro_canales=request.form.get('nro_canales'))
            db.session.add(nuevo_daq)
            db.session.flush()
            zona_daq = DAQPorZona(id_daq=nuevo_daq.id, id_zona=request.form.get('zona_puente'), id_estructura=id_puente)
            db.session.add(zona_daq)
            caract = DescripcionDAQ(id_daq=nuevo_daq.id, caracteristicas=request.form.get('caracteristicas'))
            db.session.add(caract)
            estado_nuevo_daq = EstadoDAQ(id_daq=nuevo_daq.id, fecha_estado=datetime.now(), detalles='Conectado')
            db.session.add(estado_nuevo_daq)
            canales = []
            for i in range(1,int(nuevo_daq.nro_canales)+1):
                x = Canal(id_daq=nuevo_daq.id, numero_canal=i)
                canales.append(x)
            db.session.bulk_save_objects(canales)                
            db.session.commit()
            return redirect(url_for('views_api.daqs_de_estructura',id_puente = id_puente))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))


#PERMISOS = Administrador
@views_api.route('/sensores_estructura_test/<int:id>',methods=["GET","POST"])
@login_required
def sensores_de_estructura_test(id):
    if(current_user.permisos == "Administrador"):
        if(request.method == "GET"):
            sensores_actuales = db.session.query(Sensor.id, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ZonaEstructura.descripcion, InstalacionSensor.fecha_instalacion, SensorInstalado.es_activo).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc()).all()
            print(sensores_actuales, file=sys.stderr)
            context = {
                'id_puente' : id,
                'fecha_actual' : datetime.now().strftime('%Y-%m-%d'),
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
                'sensores_puente' : sensores_actuales
            }
            return render_template('sensores_puente_test.html',**context)
        elif(request.method == "POST"):
            fecha = request.form.get('date')
            x = db.session.query(Sensor.id, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ZonaEstructura.descripcion, InstalacionSensor.fecha_instalacion, SensorInstalado.es_activo).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ZonaEstructura.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id, InstalacionSensor.fecha_instalacion <= fecha).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc()).subquery()
            sensores = db.session.query(x).filter(x.c.es_activo == True)
            print(sensores, file=sys.stderr)
            context = {
                'id_puente' : id,
                'fecha_actual' : request.form.get('date'),
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
                'sensores_puente' : sensores
            }
            return render_template('sensores_puente_test.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))
    
    
    