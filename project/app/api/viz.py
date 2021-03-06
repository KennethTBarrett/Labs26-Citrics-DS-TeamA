from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional

import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go

router = APIRouter()

# Five years ago
five_yrs = datetime.now().year - 5

statecodes = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut',
    'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida',
    'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois',
    'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky',
    'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
    'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
    'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire',
    'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
    'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
    'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming'
}


@router.get('/viz/{statecode}')
async def unemployment_visualization(statecode: str,
              statecode2: Optional[str] = None,
              statecode3: Optional[str] = None,
              view: Optional[str] = None):
    """
    Visualize state unemployment rate from [Federal Reserve Economic Data](https://fred.stlouisfed.org/) 📈

    ### Path Parameter
    `statecode`: The [USPS 2 letter abbreviation](https://en.wikipedia.org/wiki/List_of_U.S._state_and_territory_abbreviations#Table)
    (case insensitive) for any of the 50 states or the District of Columbia.

    ### Query Parameters (Optional)
    `statecode2`: The state code for a state to compare to.

    `statecode3`: The state code for a third state to compare to.

    `view`: If 'True' (string), returns a PNG instead of JSON.


    ### Response
    JSON string to render with [react-plotly.js](https://plotly.com/javascript/react/)
    """

    # Validate the state code

    statecode = statecode.upper()
    if statecode2:
        statecode2 = statecode2.upper()
    if statecode3:
        statecode3 = statecode3.upper()

    if statecode not in statecodes:
        raise HTTPException(status_code=404,
                            detail=f'State code {statecode} not found')
    if statecode2 not in statecodes and statecode2:
        raise HTTPException(status_code=404,
                            detail=f'State code {statecode2} not found')
    if statecode3 not in statecodes and statecode3:
        raise HTTPException(status_code=404,
                            detail=f'State code {statecode3} not found')

    # CASE: Statecode 1 = 2 = 3
    if statecode == statecode2 == statecode3:
        statecode2, statecode3 = None, None
    # CASE: Statecode 1 = 3
    if statecode == statecode3:
        statecode3 = None
    # CASE: Statecode 2 = 3
    if statecode2 == statecode3:
        statecode3 = None
    # CASE: Statecode 1 = 2
    if statecode == statecode2:
        if statecode3:
            statecode2 = statecode3
            statecode3 = None
        else:
            statecode2 = None

    if statecode and not statecode2 and not statecode3:
        if view and view.title() == 'True':
            return single(statecode, 'True')
        else:
            return single(statecode)
    if statecode and statecode2 and not statecode3:
        if view and view.title() == 'True':
            return two(statecode, statecode2, 'True')
        else:
            return two(statecode, statecode2)
    if statecode and statecode2 and statecode3:
        if view and view.title() == 'True':
            return three(statecode, statecode2, statecode3, 'True')
        else:
            return three(statecode, statecode2, statecode3)


def single(statecode, view=None):
    """Single state visualization"""

    statename = statecodes.get(statecode)
    # Get the state's unemployment rate data from FRED
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={statecode}UR'
    df = pd.read_csv(url, parse_dates=['DATE'])

    # Get USA general unemployment rate data from FRED.
    us_url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE'
    df_us = pd.read_csv(us_url, parse_dates=['DATE'])

    # Set column names for datasets.
    df.columns, df_us.columns = ['Date', 'Percent'], ['Date', 'Percent']

    # Restructure US to match state unemployment start dates.
    df_us = df_us[(df_us['Date'].dt.year >= min(df['Date'].dt.year)) &
                  (df_us['Date'].dt.month >= min(df['Date'].dt.month)) &
                  (df_us['Date'].dt.day >= min(df['Date'].dt.day))]

    # Styling
    style = dict()
    # United States
    us_5yrs = np.mean(df_us[(df_us['Date'].dt.year == five_yrs)]['Percent'])
    # State
    st_5yrs = np.mean(df[(df['Date'].dt.year == five_yrs)]['Percent'])

    # Make comparisons.
    if st_5yrs > us_5yrs:
        style['title'] = f'{statename} Unemployment Rates Averaged Higher than the United States since {five_yrs}.'
        style['state1color'] = '#CC0000'  # Dark error red
        style['us_color'] = '#4BB543'  # Success Green
    elif st_5yrs < us_5yrs:
        style['title'] = f'{statename} Unemployment Rates Averaged Lower than the United States since {five_yrs}.'
        style['state1color'] = '#4BB543'  # Success Green
        style['us_color'] = '#CC0000'  # Dark error red
    elif st_5yrs == us_5yrs:
        style['title'] = f'{statename} Averaged the Same Unemployment as the United States since {five_yrs}.'
        style['state1color'] = '#4BB543'  # Success Green
        style['us_color'] = 'darkcyan'  # Dark cyan

    # Set background to be transparent.
    layout = go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # Instantiate figure.
    fig = go.Figure(layout=layout)

    # Add state to figure.
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Percent'],
                             name=statename,
                             line=dict(color=style.get('state1color'))))
    # Add US to figure.
    fig.add_trace(go.Scatter(x=df_us['Date'], y=df_us['Percent'],
                             name='United States',
                             line=dict(color=style.get('us_color'),
                                       dash='dash')))

    # Title and axes.
    fig.update_layout(title_text=style.get('title'),
                      font=dict(family='Open Sans, extra bold', size=9),
                      legend_title='States')
    fig.update_xaxes(title='Date')
    fig.update_yaxes(title='Percent Unemployed')

    if view:
        img = fig.to_image(format="png")
        return StreamingResponse(io.BytesIO(img), media_type="image/png")
    else:
        return fig.to_json()


def two(statecode, statecode2, view=None):
    """Creates and styles a visualization to compare 2 states' unemployment"""
    statename = statecodes.get(statecode)
    state2 = statecodes.get(statecode2)

    # Get the state's unemployment rate data from FRED
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={statecode}UR'
    df = pd.read_csv(url, parse_dates=['DATE'])

    # Get second state's data from FRED.
    url_2 = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={statecode2}UR'
    df_2 = pd.read_csv(url_2, parse_dates=['DATE'])
    df_2.columns = ['Date', 'Percent']

    # Get USA general unemployment rate data from FRED.
    us_url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE'
    df_us = pd.read_csv(us_url, parse_dates=['DATE'])

    # Set column names for datasets.
    df.columns, df_us.columns = ['Date', 'Percent'], ['Date', 'Percent']

    # Restructure US to match state unemployment start dates.
    df_us = df_us[(df_us['Date'].dt.year >= min(df['Date'].dt.year)) &
                  (df_us['Date'].dt.year >= min(df_2['Date'].dt.year)) &
                  (df_us['Date'].dt.month >= min(df['Date'].dt.month)) &
                  (df_us['Date'].dt.month >= min(df_2['Date'].dt.month)) &
                  (df_us['Date'].dt.day >= min(df['Date'].dt.day)) &
                  (df_us['Date'].dt.day >= min(df_2['Date'].dt.day))]
    # Styling
    style = dict()
    # State
    st_5yrs = np.mean(df[(df['Date'].dt.year == five_yrs)]['Percent'])
    # State 2
    st2_5yrs = np.mean(df_2[(df_2['Date'].dt.year == five_yrs)]['Percent'])

    # Make comparisons.
    if st_5yrs > st2_5yrs:
        style['title'] = f'{statename} Averaged Higher Unemployment than {state2} since {five_yrs}.'
        style['state1color'] = '#CC0000'  # Dark error red
        style['state2color'] = '#4BB543'  # Success green
        style['us_color'] = 'black'
    elif st_5yrs < st2_5yrs:
        style['title'] = f'{statename} Averaged Lower Unemployment than {state2} since {five_yrs}.'
        style['state1color'] = '#4BB543'  # Success green
        style['state2color'] = '#CC0000'  # Dark error red
        style['us_color'] = 'black'
    elif st_5yrs == st2_5yrs:
        style['title'] = f'{statename} and {state2} Averaged the Same Unemployment since {five_yrs}.'
        style['state1color'] = '#4BB543'  # Success Green
        style['state2color'] = 'darkcyan'  # Dark Cyan
        style['us_color'] = 'black'

    # Set background to be transparent.
    layout = go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # Instantiate figure.
    fig = go.Figure(layout=layout)

    # Add state to figure.
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Percent'],
                             name=statename,
                             line=dict(color=style.get('state1color'))))
    # Add second state to figure.
    fig.add_trace(go.Scatter(x=df_2['Date'], y=df_2['Percent'],
                             name=state2,
                             line=dict(color=style.get('state2color'))))
    # Add US to figure.
    fig.add_trace(go.Scatter(x=df_us['Date'], y=df_us['Percent'],
                             name='United States',
                             line=dict(color=style.get('us_color'),
                                       dash='dash')))
    # Title and axes.
    fig.update_layout(title_text=style.get('title'),
                      font=dict(family='Open Sans, extra bold', size=9),
                      legend_title='States',
                      height=412,
                      width=640)
    fig.update_xaxes(title='Date')
    fig.update_yaxes(title='Percent Unemployed')

    if view:
        img = fig.to_image(format="png")
        return StreamingResponse(io.BytesIO(img), media_type="image/png")
    else:
        return fig.to_json()


def three(statecode, statecode2, statecode3, view=None):
    """Creates and styles a visualization to compare 3 states' unemployment"""
    statename = statecodes.get(statecode)
    state2 = statecodes.get(statecode2)
    state3 = statecodes.get(statecode3)

    # Get the state's unemployment rate data from FRED
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={statecode}UR'
    df = pd.read_csv(url, parse_dates=['DATE'])

    # Get second state's data from FRED.
    url_2 = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={statecode2}UR'
    df_2 = pd.read_csv(url_2, parse_dates=['DATE'])
    df_2.columns = ['Date', 'Percent']

    # Get third state's data from FRED.
    url_3 = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={statecode3}UR'
    df_3 = pd.read_csv(url_3, parse_dates=['DATE'])
    df_3.columns = ['Date', 'Percent']

    # Get USA general unemployment rate data from FRED.
    us_url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE'
    df_us = pd.read_csv(us_url, parse_dates=['DATE'])

    # Set column names for datasets.
    df.columns, df_us.columns = ['Date', 'Percent'], ['Date', 'Percent']

    # Restructure US to match state unemployment start dates.
    df_us = df_us[(df_us['Date'].dt.year >= min(df['Date'].dt.year)) &
                  (df_us['Date'].dt.year >= min(df_2['Date'].dt.year)) &
                  (df_us['Date'].dt.year >= min(df_3['Date'].dt.year)) &
                  (df_us['Date'].dt.month >= min(df['Date'].dt.month)) &
                  (df_us['Date'].dt.month >= min(df_2['Date'].dt.month)) &
                  (df_us['Date'].dt.month >= min(df_3['Date'].dt.month)) &
                  (df_us['Date'].dt.day >= min(df['Date'].dt.day)) &
                  (df_us['Date'].dt.day >= min(df_2['Date'].dt.day)) &
                  (df_us['Date'].dt.day >= min(df_3['Date'].dt.day))]
    # Styling
    style = dict()
    # State
    st_5yrs = np.mean(df[(df['Date'].dt.year == five_yrs)]['Percent'])
    # State 2
    st2_5yrs = np.mean(df_2[(df_2['Date'].dt.year == five_yrs)]['Percent'])
    # State 3
    st3_5yrs = np.mean(df_3[(df_3['Date'].dt.year == five_yrs)]['Percent'])

    if (st_5yrs > st2_5yrs) and (st2_5yrs > st3_5yrs):
        style['title'] = f'{statename} Averaged Higher Unemployment than {state2} and {state3} since {five_yrs}.'
        style['state1color'] = '#CC0000'  # Dark error red
        style['state2color'] = 'darkcyan'  # Dark Cyan
        style['state3color'] = '#4BB543'  # Success green
        style['us_color'] = 'black'

    elif (st_5yrs > st3_5yrs) and (st3_5yrs > st2_5yrs):
        style['title'] = f'{statename} Averaged Higher Unemployment than {state2} and {state3} since {five_yrs}.'
        style['state1color'] = '#CC0000'  # Dark error red
        style['state2color'] = '#4BB543'  # Success green
        style['state3color'] = 'darkcyan'  # Dark cyan
        style['us_color'] = 'black'

    elif (st2_5yrs > st_5yrs) and (st_5yrs > st3_5yrs):
        style['title'] = f'{statename} Averaged Higher Unemployment than {state3}, but lower than {state2} since {five_yrs}.'
        style['state1color'] = 'darkcyan'  # Dark cyan
        style['state2color'] = '#CC0000'  # Dark error red
        style['state3color'] = '#4BB543'  # Success green
        style['us_color'] = 'black'

    elif (st2_5yrs > st3_5yrs) and (st3_5yrs > st_5yrs):
        style['title'] = f'{statename} Averaged Lower Unemployment than {state2} and {state3} since {five_yrs}.'
        style['state1color'] = '#4BB543'  # Success green
        style['state2color'] = '#CC0000'  # Dark error red
        style['state3color'] = 'darkcyan'  # Dark cyan
        style['us_color'] = 'black'

    elif (st3_5yrs > st2_5yrs) and (st2_5yrs > st_5yrs):
        style['title'] = f'{statename} Averaged Lower Unemployment than {state2} and {state3} since {five_yrs}.'
        style['state1color'] = '#4BB543'  # Success green
        style['state2color'] = 'darkcyan'  # Dark cyan
        style['state3color'] = '#CC0000'  # Dark error red
        style['us_color'] = 'black'

    elif (st3_5yrs > st_5yrs) and (st_5yrs > st2_5yrs):
        style['title'] = f'{statename} Averaged Lower Unemployment than {state3}, but higher than {state2} since {five_yrs}.'
        style['state1color'] = 'darkcyan'  # Dark cyan
        style['state2color'] = '#4BB543'  # Success green
        style['state3color'] = '#CC0000'  # Dark error red
        style['us_color'] = 'black'
    # Set background to be transparent.
    layout = go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # Instantiate figure.
    fig = go.Figure(layout=layout)

    # Add state to figure.
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Percent'],
                             name=statename,
                             line=dict(color=style.get('state1color'))))
    # Add US to figure.
    fig.add_trace(go.Scatter(x=df_us['Date'], y=df_us['Percent'],
                             name='United States',
                             line=dict(color=style.get('us_color'),
                                       dash='dash')))

    fig.add_trace(go.Scatter(x=df_2['Date'], y=df_2['Percent'],
                             name=state2,
                             line=dict(color=style.get('state2color'))))

    fig.add_trace(go.Scatter(x=df_3['Date'], y=df_3['Percent'],
                             name=state3,
                             line=dict(color=style.get('state3color'))))
    # Title and axes.
    fig.update_layout(title_text=style.get('title'),
                      font=dict(family='Open Sans, extra bold', size=9),
                      legend_title='States')
    fig.update_xaxes(title='Date')
    fig.update_yaxes(title='Percent Unemployed')

    if view:
        img = fig.to_image(format="png")
        return StreamingResponse(io.BytesIO(img), media_type="image/png")
    else:
        return fig.to_json()
