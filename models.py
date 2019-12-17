from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.String(100), primary_key=True)
    nombre = db.Column(db.String(20))
    apellido = db.Column(db.String(20))
    contrasena = db.Column(db.String(200))
    permisos = db.Column(db.String(20))

class TipoZona(db.Model):
    __tablename__ = 'tipos_de_zona'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True)
    nombre_zona = db.Column(db.String(20))

class ZonaEstructura(db.Model):
    __tablename__ = 'zonas_estructura'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True)
    id_estructura = db.Column(db.Integer, db.ForeignKey('inventario_puentes.estructuras.id'), primary_key=True)
    tipo_zona = db.Column(db.Integer, db.ForeignKey('inventario_puentes.tipos_de_zona.id'))
    material = db.Column(db.String(20))
    descripcion = db.Column(db.String(1000))
        
class Estructura(db.Model):
    __tablename__ = 'estructuras'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    rol = db.Column(db.String(20))
    nombre_camino = db.Column(db.String(1000))
    cauce_queb = db.Column(db.String(100))
    provincia = db.Column(db.String(100))
    region = db.Column(db.String(100))
    largo = db.Column(db.Float)
    ancho_total = db.Column(db.Float)
    tipo_activo = db.Column(db.String(100))
    mat_estrib = db.Column(db.String(100))
    mat_cepas = db.Column(db.String(100))
    num_cepas = db.Column(db.Float)
    piso = db.Column(db.String(100))
    mat_vigas = db.Column(db.String(100))
    coord_x = db.Column(db.Float)
    coord_y = db.Column(db.Float)

class TipoSensor(db.Model):
    __tablename__ = 'tipos_de_sensor'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer,primary_key=True)
    nombre = db.Column(db.String(20))
    unidad_medida = db.Column(db.String(10))

class Sensor(db.Model):
    __tablename__ = 'sensores'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer,primary_key=True)
    tipo_sensor = db.Column(db.Integer, db.ForeignKey('inventario_puentes.tipos_de_sensor.id'))
    frecuencia = db.Column(db.Integer)
    minimo_umbral = db.Column(db.Float)
    maximo_umbral = db.Column(db.Float)
    sensibilidad = db.Column(db.Float)
    bias_level = db.Column(db.Float)
    modelo = db.Column(db.String(10))
    serial = db.Column(db.String(10))

class InstalacionSensor(db.Model):
    __tablename__ = 'instalaciones_de_sensores'
    __table_args__ = {'schema':'inventario_puentes'}    
    id = db.Column(db.Integer, primary_key=True)
    fecha_instalacion = db.Column(db.DateTime)

class SensorInstalado(db.Model):
    __tablename__ = 'sensores_instalados'
    id = db.Column(db.Integer, primary_key=True)
    id_instalacion = db.Column(db.Integer, db.ForeignKey('inventario_puentes.instalaciones_de_sensores.id'))
    id_sensor = db.Column(db.Integer, db.ForeignKey('inventario_puentes.sensores.id'))
    id_zona = db.Column(db.Integer)
    id_estructura = db.Column(db.Integer)
    conexion_actual = db.Column(db.Integer, db.ForeignKey('inventario_puentes.canales.id'))
    es_activo = db.Column(db.Boolean)
    coord_x = db.Column(db.Float)
    coord_y = db.Column(db.Float)
    coord_z = db.Column(db.Float)
    nombre_tabla = db.Column(db.String(1000))
    __table_args__ = (db.ForeignKeyConstraint(['id_zona','id_estructura'],['inventario_puentes.zonas_estructura.id','inventario_puentes.zonas_estructura.id_estructura']),{'schema':'inventario_puentes'})  

class DescripcionSensor(db.Model):
    __tablename__ = 'descripciones_de_sensores'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True)
    id_sensor_instalado = db.Column(db.Integer, db.ForeignKey('inventario_puentes.sensores_instalados.id'))
    descripcion = db.Column(db.String(1000))

class EstadoSensor(db.Model):
    __tablename__ = 'estados_sensores'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_sensor_instalado = db.Column(db.Integer, db.ForeignKey('inventario_puentes.sensores_instalados.id'), primary_key=True)
    fecha_estado = db.Column(db.DateTime, primary_key=True)
    detalles = db.Column(db.String(1000))

class CalibracionSensor(db.Model):
    __tablename__ = 'calibraciones_sensores'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_sensor_instalado = db.Column(db.Integer, db.ForeignKey('inventario_puentes.sensores_instalados.id'), primary_key=True)
    fecha_calibracion = db.Column(db.DateTime, primary_key=True)
    detalles = db.Column(db.String(1000))

class DAQ(db.Model):
    __tablename__ = 'daqs'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer,primary_key=True)
    coord_x = db.Column(db.Float)
    coord_y = db.Column(db.Float)
    coord_z = db.Column(db.Float)
    nro_canales = db.Column(db.Integer)

class DAQPorZona(db.Model):
    __tablename__ = 'daqs_por_zonas'
    id_daq = db.Column(db.Integer,db.ForeignKey('inventario_puentes.daqs.id'), primary_key=True)
    id_zona = db.Column(db.Integer, primary_key=True)
    id_estructura = db.Column(db.Integer, primary_key=True)
    __table_args__ = (db.ForeignKeyConstraint(['id_zona','id_estructura'],['inventario_puentes.zonas_estructura.id','inventario_puentes.zonas_estructura.id_estructura']),{'schema':'inventario_puentes'})

class RevisionDAQ(db.Model):
    __tablename__ = 'revisiones_de_daqs'
    __table_args__ = {'schema':'inventario_puentes'}
    id_daq = db.Column(db.Integer, db.ForeignKey('inventario_puentes.daqs.id'))    
    id_revision = db.Column(db.Integer, primary_key=True)
    fecha_revision = db.Column(db.DateTime)
    detalles = db.Column(db.String(1000))

class DescripcionDAQ(db.Model):
    __tablename__ = 'descripciones_de_daqs'
    __table_args__ = {'schema':'inventario_puentes'}
    id_daq = db.Column(db.Integer, db.ForeignKey('inventario_puentes.daqs.id'))
    id_tipo = db.Column(db.Integer, primary_key=True)
    caracteristicas = db.Column(db.String(100))

class EstadoDAQ(db.Model):
    __tablename__ = 'estados_de_daqs'
    __table_args__ = {'schema':'inventario_puentes'}
    id_estado = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_daq = db.Column(db.Integer, db.ForeignKey('inventario_puentes.daqs.id'))
    fecha_estado = db.Column(db.DateTime)
    detalles = db.Column(db.String(1000))

class Canal(db.Model):
    __tablename__ = 'canales'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True)
    id_daq = db.Column(db.Integer, db.ForeignKey('inventario_puentes.daqs.id'))
    numero_canal = db.Column(db.Integer)

class ConexionPasada(db.Model):
    __tablename__ = 'conexiones_pasadas'
    __table_args__ = {'schema':'inventario_puentes'}
    id_sensor_instalado = db.Column(db.Integer, db.ForeignKey('inventario_puentes.sensores_instalados.id'),primary_key=True)
    id_canal = db.Column(db.Integer, db.ForeignKey('inventario_puentes.canales.id'), primary_key=True)
    fecha_inicio = db.Column(db.DateTime, primary_key=True)
    fecha_termino = db.Column(db.DateTime, primary_key=True)

class Conjunto(db.Model):
    __tablename__ = 'conjuntos'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer,primary_key=True)
    nombre = db.Column(db.String(20))
    es_weather_station = db.Column(db.Boolean)
    
class WeatherStation(db.Model):
    __tablename__ = 'weather_stations'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(1000))

class ConjuntoWeatherStation(db.Model):
    __tablename__ = 'conjuntos_weather_stations'
    __table_args__ = {'schema':'inventario_puentes'}
    id_weather_station = db.Column(db.Integer, db.ForeignKey('inventario_puentes.weather_stations.id'),primary_key=True)
    id_conjunto = db.Column(db.Integer, db.ForeignKey('inventario_puentes.conjuntos.id'),primary_key=True)   

class ConjuntoZona(db.Model):
    __tablename__ = 'conjuntos_zonas'
    __table_args__ = {'schema':'inventario_puentes'}
    id_conjunto = db.Column(db.Integer, db.ForeignKey('inventario_puentes.conjuntos.id'), primary_key=True)
    id_zona = db.Column(db.Integer, primary_key=True)
    id_estructura = db.Column(db.Integer, primary_key=True)
    __table_args__ = (db.ForeignKeyConstraint(['id_zona','id_estructura'],['inventario_puentes.zonas_estructura.id','inventario_puentes.zonas_estructura.id_estructura']),{'schema':'inventario_puentes'})

class ConjuntoSensorInstalado(db.Model):
    __tablename__ = 'conjuntos_sensores'
    __table_args__ = {'schema':'inventario_puentes'}
    id_conjunto = db.Column(db.Integer, db.ForeignKey('inventario_puentes.conjuntos.id'), primary_key=True)
    id_sensor_instalado = db.Column(db.Integer, db.ForeignKey('inventario_puentes.sensores_instalados.id'), primary_key=True)

class EstadoMonitoreo(db.Model):
    __tablename__ = 'estados_de_monitoreo'
    __table_args__ = {'schema':'inventario_puentes'}
    id_estructura = db.Column(db.Integer, db.ForeignKey('inventario_puentes.estructuras.id'), primary_key=True)
    fecha_estado = db.Column(db.DateTime, primary_key=True)
    estado = db.Column(db.String(20))

class VisualizacionBIM(db.Model):
    __tablename__ = 'visualizaciones_bim'
    __table_args__ = {'schema':'inventario_puentes'}
    id_estructura = db.Column(db.Integer, db.ForeignKey('inventario_puentes.estructuras.id'), primary_key=True)
    id_archivo = db.Column(db.Integer, primary_key=True)
    ruta_acceso_archivo = db.Column(db.String(100))

class ImagenEstructura(db.Model):
    __tablename__ = 'imagenes_estructura'
    __table_args__ = {'schema':'inventario_puentes'}
    id_estructura = db.Column(db.Integer, db.ForeignKey('inventario_puentes.estructuras.id'), primary_key=True)
    id_archivo = db.Column(db.Integer, primary_key=True)
    ruta_acceso_archivo = db.Column(db.String(100))
    descripcion = db.Column(db.String(2000))

class InformeMonitoreoVisual(db.Model):
    __tablename__ = 'informes_monitoreo_visual'
    __table_args__ = {'schema':'inventario_puentes'}
    id_informe = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.String(100), db.ForeignKey('inventario_puentes.usuarios.id'))
    id_estructura = db.Column(db.Integer, db.ForeignKey('inventario_puentes.estructuras.id'))
    contenido = db.Column(db.String(2000))
    fecha = db.Column(db.DateTime)

class InformeZona(db.Model):
    __tablename__ = 'informes_por_zona'
    id_informe = db.Column(db.Integer, db.ForeignKey('inventario_puentes.informes_monitoreo_visual.id_informe'), primary_key=True)
    id_zona = db.Column(db.Integer, primary_key=True)
    id_estructura = db.Column(db.Integer, primary_key=True)
    __table_args__ = (db.ForeignKeyConstraint(['id_zona','id_estructura'],['inventario_puentes.zonas_estructura.id','inventario_puentes.zonas_estructura.id_estructura']),{'schema':'inventario_puentes'})

class HallazgoVisual(db.Model):
    __tablename__ = 'hallazgos_visuales'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.String(100), db.ForeignKey('inventario_puentes.usuarios.id'))
    detalle_hallazgo = db.Column(db.String(2000))
    fecha = db.Column(db.DateTime)
    coord_x = db.Column(db.Float)
    coord_y = db.Column(db.Float)
    coord_z = db.Column(db.Float)
    id_zona = db.Column(db.Integer)
    id_estructura = db.Column(db.Integer)
    __table_args__ = (db.ForeignKeyConstraint(['id_zona','id_estructura'],['inventario_puentes.zonas_estructura.id','inventario_puentes.zonas_estructura.id_estructura']),{'schema':'inventario_puentes'})

class HallazgoInforme(db.Model):
    __tablename__ = 'hallazgos_por_informes'
    __table_args__ = {'schema':'inventario_puentes'}
    id_informe = db.Column(db.Integer, db.ForeignKey('inventario_puentes.informes_monitoreo_visual.id_informe'), primary_key=True)
    id_hallazgo = db.Column(db.Integer, db.ForeignKey('inventario_puentes.hallazgos_visuales.id'), primary_key=True)

class MaterialAudiovisual(db.Model):
    __tablename__ = 'materiales_audiovisual'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.String(10), primary_key=True)
    id_hallazgo = db.Column(db.Integer, db.ForeignKey('inventario_puentes.hallazgos_visuales.id'), primary_key=True)
    tipo_material = db.Column(db.String(10))
    ruta_acceso_archivo = db.Column(db.String(100))

class CamaraMonitoreo(db.Model):
    __tablename__ = 'camaras_de_monitoreo'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True)
    direccion_camara = db.Column(db.String(10))
    coord_x = db.Column(db.Float)
    coord_y = db.Column(db.Float)
    coord_z = db.Column(db.Float)
    id_zona = db.Column(db.Integer)
    id_estructura = db.Column(db.Integer)
    __table_args__ = (db.ForeignKeyConstraint(['id_zona','id_estructura'],['inventario_puentes.zonas_estructura.id','inventario_puentes.zonas_estructura.id_estructura']),{'schema':'inventario_puentes'})
    
class GrupoDefinidoUsuario(db.Model):
    __tablename__ = 'grupos_definidos_por_usuario'
    __table_args__ = {'schema':'inventario_puentes'}
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    id_usuario = db.Column(db.String(100), db.ForeignKey('inventario_puentes.usuarios.id'))    
    
class SensorPorGrupoDefinido(db.Model):
    __tablename__ = 'sensores_grupos_definidos_por_usuario'
    __table_args__ = {'schema':'inventario_puentes'}    
    id_sensor_instalado = db.Column(db.Integer, db.ForeignKey('inventario_puentes.sensores_instalados.id'),primary_key=True)
    id_grupo = db.Column(db.Integer, db.ForeignKey('inventario_puentes.grupos_definidos_por_usuario.id'),primary_key=True)
