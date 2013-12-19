#!/usr/bin/env python
# coding: utf8
from gluon import *
from sqlhtml import *

def inline_row(form, fields):
        """1 row table"""
        table=TABLE(_class='web2py_editable_table')
        row=TR()
        for id, label, controls, help in fields: 
            _controls = TD(controls, _class='edit-cell', _display='table-cell', _nowrap='nowrap')
            row.append(_controls)
        table.append(row)
        return table

class SQLFORM_INLINE(SQLFORM):

    @staticmethod
    def inline_grid(query,
             inline_edit = True,
             fields=None,
             field_id=None,
             left=None,
             headers={},
             orderby=None,
             groupby=None,
             searchable=True,
             sortable=True,
             paginate=20,
             deletable=True,
             editable=True,
             details=True,
             selectable=None,
             create=True,
             csv=True,
             links=None,
             links_in_grid=True,
             upload='<default>',
             args=[],
             user_signature=True,
             maxtextlengths={},
             maxtextlength=20,
             onvalidation=None,
             onfailure=None,
             oncreate=None,
             onupdate=None,
             ondelete=None,
             sorter_icons=(XML('&#x25B2;'), XML('&#x25BC;')),
             ui = 'web2py',
             showbuttontext=True,
             _class="web2py_grid",
             formname='web2py_grid',
             search_widget='default',
             ignore_rw = False,
             formstyle = 'table3cols',
             exportclasses = None,
             formargs={},
             createargs={},
             editargs={},
             viewargs={},
             selectable_submit_button='Submit',
             buttons_placement = 'right',
             links_placement = 'right',
             noconfirm=False,
             cache_count=None,
             client_side_delete=False,
             ignore_common_filters=None,
             ):

        # jQuery UI ThemeRoller classes (empty if ui is disabled)
        if ui == 'jquery-ui':
            ui = dict(widget='ui-widget',
                      header='ui-widget-header',
                      content='ui-widget-content',
                      default='ui-state-default',
                      cornerall='ui-corner-all',
                      cornertop='ui-corner-top',
                      cornerbottom='ui-corner-bottom',
                      button='ui-button-text-icon-primary',
                      buttontext='ui-button-text',
                      buttonadd='ui-icon ui-icon-plusthick',
                      buttonback='ui-icon ui-icon-arrowreturnthick-1-w',
                      buttonexport='ui-icon ui-icon-transferthick-e-w',
                      buttondelete='ui-icon ui-icon-trash',
                      buttonedit='ui-icon ui-icon-pencil',
                      buttontable='ui-icon ui-icon-triangle-1-e',
                      buttonview='ui-icon ui-icon-zoomin',
                      buttoncancel='ui-icon ui-icon-close',
                      buttonsubmit='ui-icon ui-icon-ok',
                      )
        elif ui == 'web2py':
            ui = dict(widget='',
                      header='',
                      content='',
                      default='',
                      cornerall='',
                      cornertop='',
                      cornerbottom='',
                      button='button btn',
                      buttontext='buttontext button',
                      buttonadd='icon plus icon-plus',
                      buttonback='icon leftarrow icon-arrow-left',
                      buttonexport='icon downarrow icon-download',
                      buttondelete='icon trash icon-trash',
                      buttonedit='icon pen icon-pencil',
                      buttontable='icon rightarrow icon-arrow-right',
                      buttonview='icon magnifier icon-zoom-in',
                      buttoncancel='icon remove icon-remove',
                      buttonsubmit='icon ok icon-ok',
                      )
        elif not isinstance(ui, dict):
            raise RuntimeError('SQLFORM.grid ui argument must be a dictionary')

        db = query._db
        T = current.T
        request = current.request
        session = current.session
        response = current.response
        logged = session.auth and session.auth.user
        wenabled = (not user_signature or logged) and not groupby
        create = wenabled and create
        editable = wenabled and editable
        deletable = wenabled and deletable
        details = details and not groupby
        rows = None

        def fetch_count(dbset):
            ##FIXME for google:datastore cache_count is ignored
            ## if it's not an integer
            if cache_count is None or isinstance(cache_count, tuple):
                if groupby:
                    c = 'count(*)'
                    nrows = db.executesql(
                        'select count(*) from (%s) _tmp;' %
                        dbset._select(c, left=left, cacheable=True,
                                      groupby=groupby,
                                      cache=cache_count)[:-1])[0][0]
                elif left:
                    c = 'count(*)'
                    nrows = dbset.select(c, left=left, cacheable=True, cache=cache_count).first()[c]
                elif dbset._db._adapter.dbengine=='google:datastore':
                    #if we don't set a limit, this can timeout for a large table
                    nrows = dbset.db._adapter.count(dbset.query, limit=1000)
                else:
                    nrows = dbset.count(cache=cache_count)
            elif isinstance(cache_count, (int, long)):
                    nrows = cache_count
            elif callable(cache_count):
                nrows = cache_count(dbset, request.vars)
            else:
                nrows = 0
            return nrows

        def url(**b):
            b['args'] = args + b.get('args', [])
            localvars = request.get_vars.copy()
            localvars.update(b.get('vars', {}))
            b['vars'] = localvars
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        def url2(**b):
            b['args'] = request.args + b.get('args', [])
            localvars = request.get_vars.copy()
            localvars.update(b.get('vars', {}))
            b['vars'] = localvars
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        referrer = session.get('_web2py_grid_referrer_' + formname, url())
        # if not user_signature every action is accessible
        # else forbid access unless
        # - url is based url
        # - url has valid signature (vars are not signed, only path_info)
        # = url does not contain 'create','delete','edit' (readonly)
        if user_signature:
            if not (
                '/'.join(str(a) for a in args) == '/'.join(request.args) or
                URL.verify(request,user_signature=user_signature,
                           hash_vars=False) or
                (request.args(len(args))=='view' and not logged)):
                session.flash = T('not authorized')
                redirect(referrer)

        def gridbutton(buttonclass='buttonadd', buttontext=T('Add'),
                       buttonurl=url(args=[]), callback=None, target=None,
                       delete=None, trap=True, noconfirm=None):
            if showbuttontext:
                return A(SPAN(_class=ui.get(buttonclass)),
                         SPAN(T(buttontext), _title=T(buttontext),
                              _class=ui.get('buttontext')),
                         _href=buttonurl,
                         callback=callback,
                         target=target,
                         delete=delete,
                         noconfirm=noconfirm,
                         _class=ui.get('button'),
                         cid=request.cid)
            else:
                return A(SPAN(_class=ui.get(buttonclass)),
                         _href=buttonurl,
                         callback=callback,
                         target=target,
                         delete=delete,
                         noconfirm=noconfirm,
                         _title=T(buttontext),
                         _class=ui.get('buttontext'),
                         cid=request.cid)

        dbset = db(query,ignore_common_filters=ignore_common_filters)
        tablenames = db._adapter.tables(dbset.query)
        if left is not None:
            if not isinstance(left, (list, tuple)):
                left = [left]
            for join in left:
                tablenames += db._adapter.tables(join)
        tables = [db[tablename] for tablename in tablenames]
        if len(tables) > 1:
            inline_edit = False
        if fields:
            #add missing tablename to virtual fields
            for table in tables:
                for k,f in table.iteritems():
                    if isinstance(f,Field.Virtual):
                        f.tablename = table._tablename
            columns = [f for f in fields if f.tablename in tablenames]
        else:
            fields = []
            columns = []
            filter1 = lambda f:isinstance(f,Field)
            filter2 = lambda f:isinstance(f,Field) and f.readable
            for table in tables:
                fields += filter(filter1, table)
                columns += filter(filter2, table)
                for k,f in table.iteritems():
                    if not k.startswith('_'):
                        if isinstance(f,Field.Virtual) and f.readable:
                            f.tablename = table._tablename
                            fields.append(f)
                            columns.append(f)
        if not field_id:
            if groupby is None:
                field_id = tables[0]._id
            elif groupby and isinstance(groupby, Field):
                field_id = groupby #take the field passed as groupby
            elif groupby and isinstance(groupby, Expression):
                field_id = groupby.first #take the first groupby field
        table = field_id.table
        tablename = table._tablename
        if not any(str(f)==str(field_id) for f in fields):
            fields = [f for f in fields]+[field_id]
        if upload == '<default>':
            upload = lambda filename: url(args=['download', filename])
            if request.args(-2) == 'download':
                stream = response.download(request, db)
                raise HTTP(200, stream, **response.headers)

        def buttons(edit=False, view=False, record=None, cancel=False):
            if editable and (request.args(-3) == 'inline_edit' or request.args(-2) == 'inline_new'):
                buttons = TD(_class='edit-buttons row_buttons %(header)s %(cornertop)s' % ui)
                wrapper = DIV()
                if view:
                    args = ['view', table._tablename, request.args[-1]]
                    href = url(args=args)
                    wrapper.append(gridbutton('buttonview', 'View',
                                              callback=href, target = formname))
                if edit:
                    href = url()
                    if showbuttontext:
                        wrapper.append(A(SPAN(LABEL(I(_class=ui.get('buttonsubmit')),
                                                    SPAN(T('Save'), _title=T('Submit')),
                                                    _for='submit_form'),
                                                INPUT(_id='submit_form', 
                                                      _type='submit', 
                                                      value='Submit',
                                                      _class='hide')),
                                          _class='submit ' + ui.get('button')))
                                 
                    else:
                        wrapper.append(A(SPAN(LABEL(I(_class=ui.get('buttonsubmit')),
                                                    _for='submit_form'),
                                                INPUT(_id='submit_form', 
                                                      _type='submit', 
                                                      value='Submit',
                                                      _class='hide'),
                                        _class='submit ' + ui.get('buttontext')))
                                        )
                if cancel:
                    wrapper.append(gridbutton('buttoncancel', 'Cancel',
                                              callback=url(), target = formname))
                buttons.append(wrapper)
            else:
                buttons = DIV(gridbutton('buttonback', 'Back', referrer),
                              _class='form_header row_buttons %(header)s %(cornertop)s' % ui)
                if edit and (not callable(edit) or edit(record)):
                    args = ['edit', table._tablename, request.args[-1]]
                    buttons.append(gridbutton('buttonedit', 'Edit',
                                              url(args=args)))
                if view:
                    args = ['view', table._tablename, request.args[-1]]
                    buttons.append(gridbutton('buttonview', 'View',
                                              url(args=args)))
                if record and links:
                    for link in links:
                        if isinstance(link, dict):
                            buttons.append(link['body'](record))
                        elif link(record):
                            buttons.append(link(record))
            return buttons

        def linsert(lst, i, x):
            """
            a = [1,2]
            linsert(a, 1, [0,3])
            a = [1, 0, 3, 2]
            """
            lst[i:i] = x

        formfooter = DIV(
            _class='form_footer row_buttons %(header)s %(cornerbottom)s' % ui)

        create_form = update_form = view_form = search_form = None
        sqlformargs = dict(formargs)
        script = """
                    jQuery(document).ready(function() {
                        function resize_table(){
                            var fname = '%s';
                            jQuery('#' + fname + ' .web2py_htmltable [title=Edit], [title=Add]').each(function(){
                                jQuery(this).attr('data-w2p_method', '');
                                jQuery(this).parent().attr('data-w2p_method', '');
                            });
                            var grid_table = jQuery('#' + fname + ' .web2py_htmltable table').first();
                            var edit_table = jQuery('#' + fname + ' .web2py_editable_table');
                            var cell_widths = new Array();
                            jQuery(grid_table).each(function() {
                                for(j=0;j<jQuery(this)[0].rows[0].cells.length;j++) {
                                    var cell = jQuery(jQuery(this)[0].rows[0].cells[j]);
                                    cell_widths[j]=cell.width();
                                    console.log(cell.width() + ' ' + cell.innerWidth() + ' ' + cell.outerWidth());
                                };
                            });
                            jQuery(edit_table).each(function() {
                                for(j=0;j<jQuery(this)[0].rows[0].cells.length;j++) {
                                    jQuery(this)[0].rows[0].cells[j].width = cell_widths[j] + 2;
                                };
                            });  
                        }
                        console.log('test');
                        resize_table();
                        $(window).on('resize', function() {
                            resize_table();
                        });                       
                    });""" % formname
        if create and request.args(-2) == 'new':
            table = db[request.args[-1]]
            sqlformargs.update(createargs)
            create_form = SQLFORM(
                table, ignore_rw=ignore_rw, formstyle=formstyle,
                _class='web2py_form',
                **sqlformargs)
            create_form.process(formname=formname,
                                next=referrer,
                                onvalidation=onvalidation,
                                onfailure=onfailure,
                                onsuccess=oncreate)
            res = DIV(buttons(), create_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res

        elif details and request.args(-3) == 'view':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(referrer)
            sqlformargs.update(viewargs)
            view_form = SQLFORM(
                table, record, upload=upload, ignore_rw=ignore_rw,
                formstyle=formstyle, readonly=True, _class='web2py_form',
                **sqlformargs)
            res = DIV(buttons(edit=editable, record=record), view_form,
                      formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res
        elif editable and request.args(-3) == 'edit':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(URL('error'))
            sqlformargs.update(editargs)
            deletable_ = deletable(record) if callable(deletable) else deletable
            update_form = SQLFORM(
                table,
                record, upload=upload, ignore_rw=ignore_rw,
                formstyle=formstyle, deletable=deletable_,
                _class='web2py_form',
                submit_button=T('Submit'),
                delete_label=T('Check to delete'),
                **sqlformargs)
            update_form.process(
                formname=formname,
                onvalidation=onvalidation,
                onfailure=onfailure,
                onsuccess=onupdate,
                next=referrer)
            res = DIV(buttons(view=details, record=record),
                      update_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res

        elif editable and request.args(-2) == 'inline_new':
            table = db[request.args[-1]]
            record = None
            fieldnames = None
            if fields:
                fieldnames = [f.name for f in columns]
            if 'id' in fieldnames:
                showid = True
                fieldnames.remove('id')
            else:
                showid = False
            sqlformargs = dict(ignore_rw=ignore_rw, formstyle=inline_row,
                                _class='web2py_inline_form', buttons=[],
                                showid=showid, fields=fieldnames)
            create_form = SQLFORM(table, **sqlformargs)
            create_form.process(
                formname=formname,
                onvalidation=onvalidation,
                onfailure=onfailure,
                onsuccess=onupdate)
            if create_form.process().accepted:
                if not client_side_delete:
                    #if it's an ajax request and we don't need to reload the
                    #entire page, let's just inform that there have been no
                    #exceptions and don't regenerate the grid
                    return LOAD(url=url(), target=formname)
                else:
                    #if it's requested that the grid gets reloaded on delete
                    #on ajax, the redirect should be on the original location
                    redirect(newloc, client_side=client_side_delete)
            elif create_form.errors:
                response.flash = T('There are errors in your form')
                return LOAD(url=url(), target=formname)
            response.js = script
            details = create_form.elements('td')

            if showid:
                details.insert(0, TD(SPAN('--'), _class='edit-cell'))
            buttons = buttons(edit=editable, view=details, record=record, cancel=deletable)
            if buttons_placement in ['left', 'both']:
                details.insert(0, buttons)
            if buttons_placement in ['right', 'both']:
                details.append(buttons)
            if links and links_in_grid:
                if links_placement in ['left', 'both']:
                    linsert(details, 0, TD())
                elif links_placement in ['right', 'both']:
                    linsert(details, -1, TD())
            create_form.element('tr', replace=TR(details))
            res = TD(create_form, _class=_class, _colspan='100%%')
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res

        elif editable and request.args(-3) == 'inline_edit':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(URL('error'))
            fieldnames = []
            if fields:
                fieldnames = [f.name for f in columns]
            if 'id' in fieldnames:
                showid = True
                fieldnames.remove('id')
            else:
                showid = False
            sqlformargs = dict(upload=upload, ignore_rw=ignore_rw,
                                formstyle=inline_row, _class='web2py_inline_form',
                                buttons=[], showid=showid, fields=fieldnames)
            update_form = SQLFORM(table, record, **sqlformargs)
            update_form.process(
                formname=formname,
                onvalidation=onvalidation,
                onfailure=onfailure,
                onsuccess=onupdate)
            response.js = script
            if update_form.process().accepted:
                
                if not client_side_delete:
                    #if it's an ajax request and we don't need to reload the
                    #entire page, let's just inform that there have been no
                    #exceptions and don't regenerate the grid
                    return LOAD(url=url(), target=formname)
                else:
                    #if it's requested that the grid gets reloaded on delete
                    #on ajax, the redirect should be on the original location
                    
                    redirect(newloc, client_side=client_side_delete)
            elif update_form.errors:
                response.flash = T('There are errors in your form')
                return LOAD(url=url(), target=formname)
            details = update_form.elements('td')
            buttons = buttons(edit=editable, view=details, record=record, cancel=deletable)
            if buttons_placement in ['left', 'both']:
                details.insert(0, buttons)
            if buttons_placement in ['right', 'both']:
                details.append(buttons)
            if links and links_in_grid:
                if links_placement in ['left', 'both']:
                    linsert(details, 0, TD())
                elif links_placement in ['right', 'both']:
                    linsert(details, -1, TD())
            update_form.element('tr', replace=TR(details))
            res = TD(update_form, _class=_class, _colspan='100%%')
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res

        elif deletable and request.args(-3) == 'delete':
            table = db[request.args[-2]]
            if not callable(deletable):
                if ondelete:
                    ondelete(table, request.args[-1])
                db(table[table._id.name] == request.args[-1]).delete()
            else:
                record = table(request.args[-1]) or redirect(URL('error'))
                if deletable(record):
                    if ondelete:
                        ondelete(table, request.args[-1])
                    record.delete_record()
            if request.ajax:
                #this means javascript is enabled, so we don't need to do
                #a redirect
                if not client_side_delete:
                    #if it's an ajax request and we don't need to reload the
                    #entire page, let's just inform that there have been no
                    #exceptions and don't regenerate the grid
                    raise HTTP(200)
                else:
                    #if it's requested that the grid gets reloaded on delete
                    #on ajax, the redirect should be on the original location
                    newloc = request.env.http_web2py_component_location
                    redirect(newloc, client_side=client_side_delete)
            else:
                #we need to do a redirect because javascript is not enabled
                redirect(referrer, client_side=client_side_delete)

        exportManager = dict(
            csv_with_hidden_cols=(ExporterCSV, 'CSV (hidden cols)'),
            csv=(ExporterCSV, 'CSV'),
            xml=(ExporterXML, 'XML'),
            html=(ExporterHTML, 'HTML'),
            json=(ExporterJSON, 'JSON'),
            tsv_with_hidden_cols=
                (ExporterTSV, 'TSV (Excel compatible, hidden cols)'),
            tsv=(ExporterTSV, 'TSV (Excel compatible)'))
        if not exportclasses is None:
            """
            remember: allow to set exportclasses=dict(csv=False) to disable the csv format
            """
            exportManager.update(exportclasses)

        export_type = request.vars._export_type
        if export_type:
            order = request.vars.order or ''
            if sortable:
                if order and not order == 'None':
                    otablename, ofieldname = order.split('~')[-1].split('.', 1)
                    sort_field = db[otablename][ofieldname]
                    exception = sort_field.type in ('date', 'datetime', 'time')
                    if exception:
                        orderby = (order[:1] == '~' and sort_field) or ~sort_field
                    else:
                        orderby = (order[:1] == '~' and ~sort_field) or sort_field

            expcolumns = [str(f) for f in columns]
            if export_type.endswith('with_hidden_cols'):
                expcolumns = []
                for table in tables:
                    for field in table:
                        if field.readable and field.tablename in tablenames:
                            expcolumns.append(field)

            if export_type in exportManager and exportManager[export_type]:
                if request.vars.keywords:
                    try:
                        dbset = dbset(SQLFORM.build_query(
                            fields, request.vars.get('keywords', '')))
                        rows = dbset.select(left=left, orderby=orderby,
                                            cacheable=True, *expcolumns)
                    except Exception, e:
                        response.flash = T('Internal Error')
                        rows = []
                else:
                    rows = dbset.select(left=left, orderby=orderby,
                                    cacheable=True, *expcolumns)

                value = exportManager[export_type]
                clazz = value[0] if hasattr(value, '__getitem__') else value
                oExp = clazz(rows)
                filename = '.'.join(('rows', oExp.file_ext))
                response.headers['Content-Type'] = oExp.content_type
                response.headers['Content-Disposition'] = \
                    'attachment;filename=' + filename + ';'
                raise HTTP(200, oExp.export(), **response.headers)

        elif request.vars.records and not isinstance(
                request.vars.records, list):
            request.vars.records = [request.vars.records]
        elif not request.vars.records:
            request.vars.records = []

        session['_web2py_grid_referrer_' + formname] = \
            url2(vars=request.get_vars)
        console = DIV(_class='web2py_console %(header)s %(cornertop)s' % ui)
        error = None
        if create:
          if inline_edit:
            add_rid = '_'.join([formname, 'add-row'])
            if showbuttontext:
                add = A(SPAN(_class=ui.get('buttonadd')),
                        SPAN(T('Add'), _title=T('Add'),
                                _class=ui.get('buttontext')),
                      callback=url(args=['inline_new', tablename]),
                      target=add_rid,
                      _class=ui.get('button'),
                      _onclick="jQuery('#%s').slideDown();" % add_rid)
            else:
                add = A(SPAN(_class=ui.get('buttonadd')),
                      _title=T('Add'),
                      callback=url(args=['inline_new', tablename]),
                      target=add_rid,
                      _class=ui.get('button'),
                      _onclick="jQuery('#%s').slideDown();" % add_rid)

          else:
            add = gridbutton(
                buttonclass='buttonadd',
                buttontext=T('Add'),
                buttonurl=url(args=['new', tablename]))
            if not searchable:
                console.append(add)
        else:
            add = ''

        if searchable:
            sfields = reduce(lambda a, b: a + b,
                             [[f for f in t if f.readable] for t in tables])
            if isinstance(search_widget, dict):
                search_widget = search_widget[tablename]
            if search_widget == 'default':
                prefix = formname == 'web2py_grid' and 'w2p' or 'w2p_%s' % formname
                search_menu = SQLFORM.search_menu(sfields, prefix=prefix)
                spanel_id = '%s_query_fields' % prefix
                sfields_id = '%s_query_panel' % prefix
                skeywords_id = '%s_keywords' % prefix
                search_widget = lambda sfield, url: CAT(FORM(
                    INPUT(_name='keywords', _value=request.vars.keywords,
                          _id=skeywords_id,
                          _onfocus="jQuery('#%s').change();jQuery('#%s').slideDown();" % (spanel_id, sfields_id)),
                    INPUT(_type='submit', _value=T('Search'), _class="btn"),
                    INPUT(_type='submit', _value=T('Clear'), _class="btn",
                          _onclick="jQuery('#%s').val('');" % skeywords_id),
                    _method="GET", _action=url), search_menu)
            form = search_widget and search_widget(sfields, url()) or ''
            console.append(add)
            console.append(form)
            keywords = request.vars.get('keywords', '')
            try:
                if callable(searchable):
                    subquery = searchable(sfields, keywords)
                else:
                    subquery = SQLFORM.build_query(sfields, keywords)
            except RuntimeError:
                subquery = None
                error = T('Invalid query')
        else:
            subquery = None

        if subquery:
            dbset = dbset(subquery)
        try:
            nrows = fetch_count(dbset)
        except:
            nrows = 0
            error = T('Unsupported query')

        order = request.vars.order or ''
        if sortable:
            if order and not order == 'None':
                otablename, ofieldname = order.split('~')[-1].split('.', 1)
                sort_field = db[otablename][ofieldname]
                exception = sort_field.type in ('date', 'datetime', 'time')
                if exception:
                    orderby = (order[:1] == '~' and sort_field) or ~sort_field
                else:
                    orderby = (order[:1] == '~' and ~sort_field) or sort_field

        headcols = []
        if selectable:
            headcols.append(TH(_class=ui.get('default')))

        ordermatch, marker = orderby, ''
        if orderby:
            #if orderby is a single column, remember to put the marker
            if isinstance(orderby, Expression):
                if orderby.first and not orderby.second:
                    ordermatch, marker = orderby.first, '~'
        ordermatch = marker + str(ordermatch)
        for field in columns:
            if not field.readable:
                continue
            key = str(field)
            header = headers.get(str(field), field.label or key)
            if sortable and not isinstance(field, Field.Virtual):
                marker = ''
                if order:
                    if key == order:
                        key, marker = '~' + order, sorter_icons[0]
                    elif key == order[1:]:
                        marker = sorter_icons[1]
                else:
                    if key == ordermatch:
                        key, marker = '~' + ordermatch, sorter_icons[0]
                    elif key == ordermatch[1:]:
                        marker = sorter_icons[1]
                header = A(header, marker, _href=url(vars=dict(
                    keywords=request.vars.keywords or '',
                    order=key)), cid=request.cid)
            headcols.append(TH(header, _class=ui.get('default')))

        toadd = []
        if links and links_in_grid:
            for link in links:
                if isinstance(link, dict):
                    toadd.append(TH(link['header'], _class=ui.get('default')))
            if links_placement in ['right', 'both']:
                headcols.extend(toadd)
            if links_placement in ['left', 'both']:
                linsert(headcols, 0, toadd)

        # Include extra column for buttons if needed.
        include_buttons_column = (details or editable or deletable or
                                  (links and links_in_grid and
                                   not all([isinstance(link, dict) for link in links])))
        if include_buttons_column:
            if buttons_placement in ['right', 'both']:
                headcols.append(TH(_class=ui.get('default','')))
            if buttons_placement in ['left', 'both']:
                headcols.insert(0, TH(_class=ui.get('default','')))

        head = TR(*headcols, **dict(_class=ui.get('header')))

        cursor = True
        #figure out what page we are one to setup the limitby
        if paginate and dbset._db._adapter.dbengine=='google:datastore':
            cursor = request.vars.cursor or True
            limitby = (0, paginate)
            try: page = int(request.vars.page or 1)-1
            except ValueError: page = 0
        elif paginate and paginate<nrows:
            try: page = int(request.vars.page or 1)-1
            except ValueError: page = 0
            limitby = (paginate*page,paginate*(page+1))
        else:
            limitby = None
        try:
            table_fields = [field for field in fields
                            if (field.tablename in tablenames and not(isinstance(field,Field.Virtual)))]
            if dbset._db._adapter.dbengine=='google:datastore':
                rows = dbset.select(left=left,orderby=orderby,
                                    groupby=groupby,limitby=limitby,
                                    reusecursor=cursor,
                                    cacheable=True,*table_fields)
                next_cursor = dbset._db.get('_lastcursor', None)
            else:
                rows = dbset.select(left=left,orderby=orderby,
                                    groupby=groupby,limitby=limitby,
                                    cacheable=True,*table_fields)
        except SyntaxError:
            rows = None
            next_cursor = None
            error = T("Query Not Supported")
        except Exception, e:
            rows = None
            next_cursor = None
            error = T("Query Not Supported: %s")%e

        message = error
        if not message and nrows:
            if dbset._db._adapter.dbengine=='google:datastore' and nrows>=1000:
                message = T('at least %(nrows)s records found') % dict(nrows=nrows)
            else:
                message = T('%(nrows)s records found') % dict(nrows=nrows)
        console.append(DIV(message or T('None'),_class='web2py_counter'))

        paginator = UL()
        if paginate and dbset._db._adapter.dbengine=='google:datastore':
            #this means we may have a la'rge table with an unknown number of rows.
            try:
                page = int(request.vars.page or 1)-1
            except ValueError:
                page = 0
            paginator.append(LI('page %s'%(page+1)))
            if next_cursor:
                d = dict(page=page+2, cursor=next_cursor)
                if order: d['order']=order
                if request.vars.keywords: d['keywords']=request.vars.keywords
                paginator.append(LI(
                    A('next',_href=url(vars=d),cid=request.cid)))
        elif paginate and paginate<nrows:
            npages, reminder = divmod(nrows, paginate)
            if reminder:
                npages += 1
            try:
                page = int(request.vars.page or 1) - 1
            except ValueError:
                page = 0

            def self_link(name, p):
                d = dict(page=p + 1)
                if order:
                    d['order'] = order
                if request.vars.keywords:
                    d['keywords'] = request.vars.keywords
                return A(name, _href=url(vars=d), cid=request.cid)
            NPAGES = 5  # window is 2*NPAGES
            if page > NPAGES + 1:
                paginator.append(LI(self_link('<<', 0)))
            if page > NPAGES:
                paginator.append(LI(self_link('<', page - 1)))
            pages = range(max(0, page - NPAGES), min(page + NPAGES, npages))
            for p in pages:
                if p == page:
                    paginator.append(LI(A(p + 1, _onclick='return false'),
                                        _class='current'))
                else:
                    paginator.append(LI(self_link(p + 1, p)))
            if page < npages - NPAGES:
                paginator.append(LI(self_link('>', page + 1)))
            if page < npages - NPAGES - 1:
                paginator.append(LI(self_link('>>', npages - 1)))
        else:
            limitby = None

        htmltable = TABLE(THEAD(head))
        htmltable.append(TBODY(TR(_id=add_rid, _class='hidden')))
        if rows:
            tbody = TBODY()
            numrec = 0
            for row in rows:
                trcols = []
                id = row[field_id]
                if inline_edit:
                    inline_rid = '_'.join([formname, str(id)])
                if selectable:
                    trcols.append(
                        INPUT(_type="checkbox", _name="records", _value=id,
                                    value=request.vars.records))
                for field in columns:
                    if not field.readable:
                        continue
                    if field.type == 'blob':
                        continue
                    value = row[str(field)]
                    maxlength = maxtextlengths.get(str(field), maxtextlength)
                    if field.represent:
                        try:
                            value = field.represent(value, row)
                        except KeyError:
                            try:
                                value = field.represent(
                                    value, row[field.tablename])
                            except KeyError:
                                pass
                    elif field.type == 'boolean':
                        value = INPUT(_type="checkbox", _checked=value,
                                      _disabled=True)
                    elif field.type == 'upload':
                        if value:
                            if callable(upload):
                                value = A(
                                    T('file'), _href=upload(value))
                            elif upload:
                                value = A(T('file'),
                                          _href='%s/%s' % (upload, value))
                        else:
                            value = ''
                    if isinstance(value, str):
                        value = truncate_string(value, maxlength)
                    elif not isinstance(value, DIV):
                        value = field.formatter(value)
                    trcols.append(TD(value))
                row_buttons = TD(_class='row_buttons',_nowrap=True)
                if links and links_in_grid:
                    toadd = []
                    for link in links:
                        if isinstance(link, dict):
                            toadd.append(TD(link['body'](row)))
                        else:
                            if link(row):
                                row_buttons.append(link(row))
                    if links_placement in ['right', 'both']:
                        trcols.extend(toadd)
                    if links_placement in ['left', 'both']:
                        linsert(trcols, 0, toadd)

                if include_buttons_column:
                    if details and (not callable(details) or details(row)):
                        row_buttons.append(gridbutton(
                            'buttonview', 'View',
                            url(args=['view', tablename, id])))
                    if editable and (not callable(editable) or editable(row)):
                        if inline_edit:
                            row_buttons.append(gridbutton(
                                'buttonedit', 'Edit',
                                buttonurl=None,
                                callback=url(args=['inline_edit', tablename, id]),
                                target=inline_rid))
                        else:
                            row_buttons.append(gridbutton(
                                'buttonedit', 'Edit',
                                url(args=['edit', tablename, id])))
                    if deletable and (not callable(deletable) or deletable(row)):
                        row_buttons.append(gridbutton(
                            'buttondelete', 'Delete',
                            url(args=['delete', tablename, id]),
                            callback=url(args=['delete', tablename, id]),
                            noconfirm=noconfirm,
                            delete='tr'))
                    if buttons_placement in ['right', 'both']:
                        trcols.append(row_buttons)
                    if buttons_placement in ['left', 'both']:
                        trcols.insert(0, row_buttons)
                if numrec % 2 == 0:
                    classtr = 'even'
                else:
                    classtr = 'odd'
                numrec += 1
                if id:
                    if inline_edit:
                        rid = inline_rid
                    else:
                        rid = id
                    if callable(rid):  # can this ever be callable?
                        rid = rid(row)
                    tr = TR(*trcols, **dict(
                            _id=rid,
                            _class='%s %s' % (classtr, 'with_id')))
                else:
                    tr = TR(*trcols, **dict(_class=classtr))
                tbody.append(tr)
            htmltable.append(tbody)
            htmltable = DIV(
                htmltable, _class='web2py_htmltable',
                _style='width:100%;overflow-x:auto;-ms-overflow-x:scroll')
            if selectable:
                if not callable(selectable):
                    #now expect that selectable and related parameters are iterator (list, tuple, etc)
                    inputs = []
                    for i, submit_info in enumerate(selectable):
                        submit_text = submit_info[0]
                        submit_class = submit_info[2] if len(submit_info) > 2 else ''

                        input_ctrl = INPUT(_type="submit", _name='submit_%d' % i, _value=T(submit_text))
                        input_ctrl.add_class(submit_class)
                        inputs.append(input_ctrl)
                else:
                    inputs = [INPUT(_type="submit", _value=T(selectable_submit_button))]

                if formstyle == 'bootstrap':
                    # add space between buttons
                    #inputs = sum([[inp, ' '] for inp in inputs], [])[:-1]
                    htmltable = FORM(htmltable, DIV(_class='form-actions', *inputs))
                else:
                    htmltable = FORM(htmltable, *inputs)

                if htmltable.process(formname=formname).accepted:
                    htmltable.vars.records = htmltable.vars.records or []
                    htmltable.vars.records = htmltable.vars.records if type(htmltable.vars.records) == list else [htmltable.vars.records]
                    records = [int(r) for r in htmltable.vars.records]
                    if not callable(selectable):
                        for i, submit_info in enumerate(selectable):
                            submit_callback = submit_info[1]
                            if htmltable.vars.get('submit_%d' % i, False):
                                submit_callback(records)
                                break
                    else:
                        selectable(records)
                    redirect(referrer)
        else:
            htmltable.append(TR(TD(T('No records found'))))

        if csv and nrows:
            export_links = []
            for k, v in sorted(exportManager.items()):
                if not v:
                    continue
                label = v[1] if hasattr(v, "__getitem__") else k
                link = url2(vars=dict(
                    order=request.vars.order or '',
                    _export_type=k,
                    keywords=request.vars.keywords or ''))
                export_links.append(A(T(label), _href=link))
            export_menu = \
                DIV(T('Export:'), _class="w2p_export_menu", *export_links)
        else:
            export_menu = None

        res = DIV(console, DIV(htmltable, _class="web2py_table"),
                  _class='%s %s' % (_class, ui.get('widget')), _id=formname)
        if paginator.components:
            res.append(
                DIV(paginator,
                    _class="web2py_paginator %(header)s %(cornerbottom)s" % ui))
        if export_menu:
            res.append(export_menu)
        res.create_form = create_form
        res.update_form = update_form
        res.view_form = view_form
        res.search_form = search_form
        res.rows = rows
        return res
