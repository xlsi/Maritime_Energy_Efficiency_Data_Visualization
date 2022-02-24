from django.shortcuts import render
from django.db import connections
from django.shortcuts import redirect
from django.http import Http404
from django.db.utils import IntegrityError

from app.utils import namedtuplefetchall, clamp
from app.forms import ImoForm
from app.forms import ShipForm
from app.forms import Verifier
from .models import Ship


PAGE_SIZE = 20
COLUMNS = [
    'imo',
    'ship_name',
    'ship_type',
    'issue_date',
    'expiry_date',
    'eedi'
]


def index(request):
    """Shows the main page"""
    context = {'nbar': 'home'}
    return render(request, 'index.html', context)


def db(request):
    """Shows very simple DB page"""
    with connections['default'].cursor() as cursor:
        cursor.execute('INSERT INTO app_greeting ("when") VALUES (NOW());')
        cursor.execute('SELECT "when" FROM app_greeting;')
        greetings = namedtuplefetchall(cursor)

    context = {'greetings': greetings, 'nbar': 'db'}
    return render(request, 'db.html', context)

# Add new block -- Aggregation
def aggregation(request):
    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT ship_type, min(eedi) as min_eedi, avg(eedi::float)::numeric(10,2) as avg_eedi, max(eedi) as max_eedi FROM co2emission_reduced GROUP BY ship_type ORDER BY ship_type;')
        rows = namedtuplefetchall(cursor)

    context = {'rows': rows, 'nbar': 'aggregation'}
    return render(request, 'project.html', context)

# Add new block -- Visual
# Need customize

def visual(request):
    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT ship_type, count(*), avg(eedi::float)::numeric(10,2) FROM co2emission_reduced GROUP BY ship_type ORDER BY ship_type;')
        rows = cursor.fetchall()
    labels = []
    data = []
    avgeedi = []
    for i in rows:
        labels.append(i[0])
        data.append(i[1])

    context = {'labels': labels, 'data': data, 'nbar': 'visual'}
    return render(request, 'visual.html', context)  

# Add new block -- Exxplore the data

COLUMNS_explore = [
            'imo', 'ship_name', 'ship_type', 
            'eiv', 'eedi', 'verify_name', 'report_period', 
            'total_co2_emission', 'total_fuel_consumption', 
            'time_at_sea', 'annual_co2_per_distance', 'annual_co2_per_trans_work'
]


def explore(request, page = 1):
    """Shows the explore table page"""
    msg = None
    order_by = request.GET.get('order_by', '')
    order_by = order_by if order_by in COLUMNS_explore else 'imo'
    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM explore_2020')
        count = cursor.fetchone()[0]
        num_pages = (count - 1) // PAGE_SIZE + 1
        page = clamp(page, 1, num_pages)
 
        offset = (page - 1) * PAGE_SIZE
        cursor.execute(f'''
            SELECT imo, ship_name, ship_type, eiv, eedi, verifier_num, report_period, 
            total_co2_emission, total_fuel_consumption, time_at_sea, annual_co2_per_distance, annual_co2_per_trans_work
            FROM explore_2020
            ORDER BY {order_by}
            OFFSET %s
            LIMIT %s;
        ''', [offset, PAGE_SIZE])
        rows = namedtuplefetchall(cursor)

    context = {
        'nbar': 'explore',
        'page': page,
        'rows': rows,
        'num_pages': num_pages,
        'msg': msg,
        'order_by': order_by
    }
    return render(request, 'explore.html', context)


def emissions(request, page=1):
    """Shows the emissions table page"""
    msg = None
    order_by = request.GET.get('order_by', '')
    order_by = order_by if order_by in COLUMNS else 'imo'

    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM co2emission_reduced')
        count = cursor.fetchone()[0]
        num_pages = (count - 1) // PAGE_SIZE + 1
        page = clamp(page, 1, num_pages)

        offset = (page - 1) * PAGE_SIZE
        cursor.execute(f'''
            SELECT {", ".join(COLUMNS)}
            FROM co2emission_reduced
            ORDER BY {order_by}
            OFFSET %s
            LIMIT %s
        ''', [offset, PAGE_SIZE])
        rows = namedtuplefetchall(cursor)

    imo_deleted = request.GET.get('deleted', False)
    if imo_deleted:
        msg = f'✔ IMO {imo_deleted} deleted'

    context = {
        'nbar': 'emissions',
        'page': page,
        'rows': rows,
        'num_pages': num_pages,
        'msg': msg,
        'order_by': order_by
    }
    return render(request, 'emissions.html', context)


def insert_update_values(form, post, action, imo):
    """
    Inserts or updates database based on values in form and action to take,
    and returns a tuple of whether action succeded and a message.
    """
    if not form.is_valid():
        return False, 'There were errors in your form'

    # Set values to None if left blank
    cols = COLUMNS[:]
    values = [post.get(col, None) for col in cols]
    values = [val if val != '' else None for val in values]

    if action == 'update':
        # Remove imo from updated fields
        cols, values = cols[1:], values[1:]
        with connections['default'].cursor() as cursor:
            cursor.execute(f'''
                UPDATE co2emission_reduced
                SET {", ".join(f"{col} = %s" for col in cols)}
                WHERE imo = %s;
            ''', [*values, imo])
        return True, '✔ IMO updated successfully'

    # Else insert
    with connections['default'].cursor() as cursor:
        cursor.execute(f'''
            INSERT INTO co2emission_reduced ({", ".join(cols)})
            VALUES ({", ".join(["%s"] * len(cols))});
        ''', values)
    return True, '✔ IMO inserted successfully'


def emission_detail(request, imo=None):
    """Shows the form where the user can insert or update an IMO"""
    success, form, msg, initial_values = False, None, None, {}
    is_update = imo is not None

    if is_update and request.GET.get('inserted', False):
        success, msg = True, f'✔ IMO {imo} inserted'

    if request.method == 'POST':
        # Since we set imo=disabled for updating, the value is not in the POST
        # data so we need to set it manually. Otherwise if we are doing an
        # insert, it will be None but filled out in the form
        if imo:
            request.POST._mutable = True
            request.POST['imo'] = imo
        else:
            imo = request.POST['imo']

        form = ImoForm(request.POST)
        action = request.POST.get('action', None)

        if action == 'delete':
            with connections['default'].cursor() as cursor:
                cursor.execute('DELETE FROM co2emission_reduced WHERE imo = %s;', [imo])
            return redirect(f'/emissions?deleted={imo}')
        try:
            success, msg = insert_update_values(form, request.POST, action, imo)
            if success and action == 'insert':
                return redirect(f'/emissions/imo/{imo}?inserted=true')
        except IntegrityError:
            success, msg = False, 'IMO already exists'
        except Exception as e:
            success, msg = False, f'Some unhandled error occured: {e}'
    elif imo:  # GET request and imo is set
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT * FROM co2emission_reduced WHERE imo = %s', [imo])
            try:
                initial_values = namedtuplefetchall(cursor)[0]._asdict()
            except IndexError:
                raise Http404(f'IMO {imo} not found')

    # Set dates (if present) to iso format, necessary for form
    # We don't use this in class, but you will need it for your project
    for field in ['issue_date', 'expiry_date']:
        if initial_values.get(field, None) is not None:
            initial_values[field] = initial_values[field].isoformat()

    # Initialize form if not done already
    form = form or ImoForm(initial=initial_values)
    if is_update:
        form['imo'].disabled = True

    context = {
        'nbar': 'emissions',
        'is_update': is_update,
        'imo': imo,
        'form': form,
        'msg': msg,
        'success': success
    }
    return render(request, 'emission_detail.html', context)

def explore_detail(request, imo=None):
    success, form, msg, initial_values = False, None, None, {}
    is_update = imo is not None
    if request.method == 'POST':
        # Since we set imo=disabled for updating, the value is not in the POST
        # data so we need to set it manually. Otherwise if we are doing an
        # insert, it will be None but filled out in the form
        if imo:
            request.POST._mutable = True
            request.POST['imo'] = imo
        else:
            imo = request.POST['imo']

        form = ShipForm(request.POST)
        action = request.POST.get('action', None)

    elif imo:  # GET request and imo is set
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT * FROM explore_2020 WHERE imo = %s', [imo])
            try:
                initial_values = namedtuplefetchall(cursor)[0]._asdict()
            except IndexError:
                raise Http404(f'IMO {imo} not found')

    # Set dates (if present) to iso format, necessary for form
    # We don't use this in class, but you will need it for your project
    for field in ['issue_date', 'expiry_date']:
        if initial_values.get(field, None) is not None:
            initial_values[field] = initial_values[field].isoformat()

    # Initialize form if not done already
    form = form or ShipForm(initial=initial_values)
    if is_update:
        form['imo'].disabled = True

    context = {
        'nbar': 'explore',
        'is_update': is_update,
        'imo': imo,
        'form': form,
        'msg': msg,
        'success': success
    }
    return render(request, 'explore_detail.html', context)

def explore_ship_name(request, ship_name=None):
    success, form, msg, initial_values = False, None, None, {}
    is_update = ship_name is not None
    # if request.method == 'POST':
    #     # Since we set imo=disabled for updating, the value is not in the POST
    #     # data so we need to set it manually. Otherwise if we are doing an
    #     # insert, it will be None but filled out in the form
    #     if ship_name:
    #         request.POST._mutable = True
    #         request.POST['ship_name'] = ship_name
    #     else:
    #         ship_name = request.POST['ship_name']

    #     form = ShipForm(request.POST)
    #     action = request.POST.get('action', None)

    # elif ship_name:  # GET request and ship_name is set
    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT * FROM explore_2020 WHERE ship_name = %s', [ship_name])
        try:
            initial_values = namedtuplefetchall(cursor)[0]._asdict()
        except IndexError:
            raise Http404(f'ship_name {ship_name} not found')

    # Set dates (if present) to iso format, necessary for form
    # We don't use this in class, but you will need it for your project
    for field in ['issue_date', 'expiry_date']:
        if initial_values.get(field, None) is not None:
            initial_values[field] = initial_values[field].isoformat()

    # Initialize form if not done already
    form = form or ShipForm(initial=initial_values)
    if is_update:
        form['ship_name'].disabled = True

    context = {
        'nbar': 'explore',
        'is_update': is_update,
        'ship_name': ship_name,
        'form': form,
        'msg': msg,
        'success': success
    }
    return render(request, 'explore_ship_name.html', context)


columns_co2 = ['verifier_country', 'ship_type', 'sum_co2_emission']


# Add new block -- total CO2 emission
def total_co2_emission(request):
    order_by = request.GET.get('order_by', '')
    order_by = order_by if order_by in columns_co2 else 'verifier_country,ship_type'
    with connections['default'].cursor() as cursor:
        cursor.execute(f'''select v.verifier_country, s.ship_type, sum(total_co2_emission) as sum_co2_emission 
                        from explore s, explore_verifier v, fact_table f where f.ship_key = s.ship_key 
                        and f.verifier_key = v.verifier_key group by cube(v.verifier_country, s.ship_type) 
                        order by {order_by} desc;''')
        rows1 = namedtuplefetchall(cursor)

    with connections['default'].cursor() as cursor:
        cursor.execute(f'''select v.verifier_country, s.ship_type, sum(total_co2_emission) as sum_co2_emission 
                        from explore s, explore_verifier v, fact_table f where f.ship_key = s.ship_key 
                        and f.verifier_key = v.verifier_key group by rollup(v.verifier_country, s.ship_type) 
                        order by {order_by} desc;''')
        rows2 = namedtuplefetchall(cursor)

    with connections['default'].cursor() as cursor:
        cursor.execute(f'''select v.verifier_country, sum(total_co2_emission) as sum_co2_emission 
                        from explore_verifier v, fact_table f where f.verifier_key = v.verifier_key 
                        group by (v.verifier_country);''')
        fig_row1 = namedtuplefetchall(cursor)
        labels = []
        for i in fig_row1:
            labels.append(i[0])
    with connections['default'].cursor() as cursor:
        cursor.execute(f'''select s.ship_type, sum(total_co2_emission) as sum_co2_emission 
                        from explore s, fact_table f where f.ship_key = s.ship_key 
                        group by (s.ship_type);''')
        fig_row2 = namedtuplefetchall(cursor)
    with connections['default'].cursor() as cursor:
        cursor.execute(f'''select v.verifier_country, s.ship_type, sum(total_co2_emission) as sum_co2_emission 
                        from explore s, explore_verifier v, fact_table f where f.ship_key = s.ship_key 
                        and f.verifier_key = v.verifier_key group by (v.verifier_country, s.ship_type);''')
        fig_row3 = namedtuplefetchall(cursor)

    context = {'rows1': rows1,
               'rows2': rows2,
               'fig_row1': fig_row1,
               'fig_row2': fig_row2,
               'fig_row3': fig_row3,
               'nbar': 'total_co2_emission'}

    return render(request, 'total_co2_emission.html', context)

