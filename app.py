import time
import plotly.express as px
import streamlit as st
import pandas as pd
import requests
import ast
import pytz
from datetime import datetime
from geopy.geocoders import Nominatim
from tzwhere import tzwhere

st.set_page_config(
    page_title="Tom Tom Web Scraping",
    page_icon="🚗",
    layout="wide"
)

geolocator = Nominatim(user_agent='tom_tom_project')
tz = tzwhere.tzwhere()

# Get timezone from city
def get_timezone(city:str):
  location = geolocator.geocode(city)
  tz_name = tz.tzNameAt(location.latitude, location.longitude)

  return tz_name

# Get time of the day from weather coding
def get_time_of_day(code:str):
  return 'Day' if code[0] == 'D' else 'Night'

# Get sky status from weather coding
def get_sky_status(code:str): 
  sky_status_code = code[2:4]
  sky_status = None
  
  if sky_status_code == 'CS':
    sky_status = 'Clear Sky'
  elif sky_status_code == 'MI':
    sky_status = 'Mist'
  elif sky_status_code == 'FO':
    sky_status = 'Fog'
  elif sky_status_code == 'SA':
    sky_status = 'Sand/dust storm'
  elif sky_status_code == 'HZ':
    sky_status = 'Hazy'
  elif sky_status_code == 'SC':
    sky_status = 'Some clouds'
  elif sky_status_code == 'PC':
    sky_status = 'Partly clouds'
  elif sky_status_code == 'CL':
    sky_status = 'Cloudly'
  elif sky_status_code == 'OC':
    sky_status = 'Overcast'
  elif sky_status_code == 'ST':
    sky_status = 'Storm'
  elif sky_status_code == 'CY':
    sky_status = 'Cyclone'
  
  return sky_status

# Get precipitation type from weather coding
def get_precipitation_type(code:str):
  precipitation_type_code = code[5:8]
  precipitation_type = None
  
  if precipitation_type_code == 'DRI':
    precipitation_type = 'Drizzle'
  elif precipitation_type_code == 'RAI':
    precipitation_type = 'Rain'
  elif precipitation_type_code == 'RAS':
    precipitation_type = 'Rain Showers'
  elif precipitation_type_code == 'RAT':
    precipitation_type = 'Rain & Thunderstorm'
  elif precipitation_type_code == 'SNO':
    precipitation_type = 'Snow'
  elif precipitation_type_code == 'SNS':
    precipitation_type = 'Snow showers'
  elif precipitation_type_code == 'SNT':
    precipitation_type = 'Snow & thunderstorm'
  elif precipitation_type_code == 'SLE':
    precipitation_type = 'Sleet'
  elif precipitation_type_code == 'SLS':
    precipitation_type = 'Sleet showers'
  elif precipitation_type_code == 'SLT':
    precipitation_type = 'Sleet & thunderstorm'
  elif precipitation_type_code == 'ICR':
    precipitation_type = 'Ice rain'
  elif precipitation_type_code == 'HAI':
    precipitation_type = 'Hail'
  elif precipitation_type_code == 'HAS':
    precipitation_type = 'Hail showers'
  elif precipitation_type_code == 'HAT':
    precipitation_type = 'Hail & thunderstorm'
  
  return precipitation_type

# Get precipitation level from weather coding
def get_precipitation_level(code:str):
  precipitation_level_code = code[-1]  
  precipitation_level = None  

  if precipitation_level_code == '1':
    precipitation_level = 'Light'
  elif precipitation_level_code == '2':
    precipitation_level = 'Moderate'
  elif precipitation_level_code == '3':
    precipitation_level = 'Heavy'
  
  return precipitation_level

# Request on url website function
def get_data(url:str):
  response = requests.get(url)
  dict_str = response.content.decode("UTF-8")

  return ast.literal_eval(dict_str)

# Function to get live hourly data for a city
@st.experimental_memo
def get_live_hourly(key:str, city:str):
  url = 'https://api.midway.tomtom.com/ranking/liveHourly'
  data = get_data(f'{url}/{key}')
  df = pd.json_normalize(data['data'])
  city_tz = pytz.timezone(get_timezone(city))

  time_tz = df['UpdateTime'].apply(lambda x: datetime.utcfromtimestamp(x/1000).replace(tzinfo=pytz.utc).astimezone(city_tz))
  weekday_time_tz = time_tz.apply(lambda x: x.strftime(format='%a %-Hh'))
  date = time_tz.apply(lambda x: x.strftime(format='%b %-d, %-Hh'))
  
  df['UpdateTimeLocal'] = date
  df['WeekdayTimeLocal'] = weekday_time_tz
  df['City'] = city

  return df[['City', 'JamsDelay', 'TrafficIndexLive', 'JamsLength', 'JamsCount', 'TrafficIndexWeekAgo', 'UpdateTimeLocal', 'WeekdayTimeLocal']].drop_duplicates()

# Function to get weather hourly data for a city
@st.experimental_memo
def get_weather_hourly(key:str, city:str):
  url = 'https://api.weather.midway.tomtom.com/weather/live'
  data = get_data(f'{url}/{key}')

  df = pd.json_normalize(data['data'])

  col = {
      'Weather.dateTimeLocal': 'DateTimeLocal', 
      'Weather.temperature': 'Temperature', 
      'Weather.weatherCode': 'WeatherCode', 
      'Weather.windSpeed': 'WindSpeed', 
      'Weather.windDirection': 'WindDirection', 
      'Weather.precipitationProbability': 'PrecipitationProbability',
      'Weather.precipitation': 'Precipitation',
      'Weather.relativeHumidity': 'RelativeHumidity'
      }
  df.rename(columns=col, inplace=True)
  df['City'] = city
  df['UpdateTimeLocal'] = df['DateTimeLocal'].apply(lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S'))
  df['TimeDay'] = df['WeatherCode'].apply(lambda x: get_time_of_day(x))
  df['SkyStatus'] = df['WeatherCode'].apply(lambda x: get_sky_status(x))
  df['PrecipitationType'] = df['WeatherCode'].apply(lambda x: get_precipitation_type(x))
  df['PrecipitationLevel'] = df['WeatherCode'].apply(lambda x: get_precipitation_level(x))

  return df[['City', 'UpdateTimeLocal', 'Temperature', 'TimeDay', 'SkyStatus', 'PrecipitationType', 'PrecipitationLevel', 'WindSpeed', \
             'WindDirection', 'PrecipitationProbability', 'Precipitation', 'RelativeHumidity']].drop_duplicates()

city_db = pd.read_csv('cities.csv')
df = pd.DataFrame()
weather_df = pd.DataFrame()

for index, row in city_db.iterrows():
  df = df.append(get_live_hourly(row['key'], row['city']))
  weather_df = weather_df.append(get_weather_hourly(row['key'], row['city']))

# Dashboard title
st.title('Tom Tom Web Scraping Dashboard')

# Top-level filters
job_filter = st.selectbox('Select a City', pd.unique(df['City']))

# Dataframe filter
df = df[df['City'] == job_filter]
weather_df = weather_df[weather_df['City'] == job_filter]

# Creating a single-element container
placeholder = st.empty()

with placeholder.container():

  # Create three columns
  kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

  # Fill in those three columns with respective metrics or KPIs
  kpi1.metric(
      label = 'Congestion Level Now',
      value = str(list(df['TrafficIndexLive'])[-1]) + ' %',
      delta = str(list(df['TrafficIndexLive'])[-1] - list(df['TrafficIndexWeekAgo'])[-1]) + ' %'
  )

  kpi2.metric(
      label = 'Total Jam Count Now',
      value = list(df['JamsCount'])[-1]
  )

  kpi3.metric(
      label = 'Total Jam Length Now',
      value = str(list(df['JamsLength'])[-1]) + ' km'
  )

  kpi4.metric(
      label = 'Temperature',
      value = str(list(weather_df['Temperature'])[-1]) + '°C'
  )

  kpi5.metric(
      label = 'Wind',
      value = str(round(list(weather_df['WindSpeed'])[-1]*3.6,1)) + ' km/h'
  )

  kpi6.metric(
      label = 'Humidity',
      value = str(list(weather_df['RelativeHumidity'])[-1]) + '%'
  )

  st.markdown('### Traffic Index')
  new_df = df[['UpdateTimeLocal', 'TrafficIndexLive', 'TrafficIndexWeekAgo']]
  new_df.rename(columns={'TrafficIndexLive':'Current Week', 'TrafficIndexWeekAgo':'Week Ago'}, inplace=True)
  chart = px.line(data_frame=new_df, x='UpdateTimeLocal', y=['Current Week', 'Week Ago'],labels={
                      "UpdateTimeLocal": "Day",
                      "value": "Traffic Index"
                  })
  st.plotly_chart(chart, use_container_width=True)
  
  fig_col1, fig_col2 = st.columns(2)
  
  with fig_col1:
    st.markdown('### Correlation Jams x Hour of Day')
    df['Hour'] = df['UpdateTimeLocal'].apply(lambda x: int(datetime.strptime(x,'%b %d, %Hh').strftime(format='%H')))
    scatter_plot = df[['Hour', 'TrafficIndexLive']].dropna().rename(columns={'TrafficIndexLive': 'Traffic Index'})
    scatter_plot = scatter_plot[(scatter_plot['Hour'] >= 8) & (scatter_plot['Hour'] <= 17)]
    fig1 = px.scatter(scatter_plot, x='Hour', y='Traffic Index')
    st.write(fig1)
  
  with fig_col2:
    st.markdown('### Traffic Index Heat Map')
    heat_map = df[['UpdateTimeLocal','TrafficIndexLive']].rename(columns={'TrafficIndexLive': 'Traffic Index'})
    heat_map = heat_map.append(df[['UpdateTimeLocal','TrafficIndexWeekAgo']].rename(columns={'TrafficIndexWeekAgo': 'Traffic Index'}))
    heat_map['Day'] = heat_map['UpdateTimeLocal'].apply(lambda x: datetime.strptime(x,'%b %d, %Hh').strftime(format='%A') + ':00')
    heat_map['Hour'] = heat_map['UpdateTimeLocal'].apply(lambda x: datetime.strptime(x,'%b %d, %Hh').strftime(format='%H'))
    heat_map['DayofWeek'] = heat_map['UpdateTimeLocal'].apply(lambda x: str(7-int(datetime.strptime(x,'%b %d, %Hh').strftime(format='%w'))))
    fig2 = px.density_heatmap(heat_map.sort_values(by=['Hour','DayofWeek'], ascending=False), x='Day', y='Hour', z='Traffic Index', histfunc='avg')
    fig2.update_traces(dict(coloraxis=None))
    st.write(fig2)