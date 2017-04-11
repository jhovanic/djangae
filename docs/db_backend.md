# The Database Backend

Previously, in order to use Django's ORM with the App Engine Datastore, django-nonrel was required, along with
djangoappengine. That's now changed. With Djangae you can use vanilla Django with the Datastore. Heavily inspired by
djangoappengine (thanks Waldemar!) Djangae provides an intelligent database backend that allows vanilla Django to be
used, and makes use of many of the Datastore's speed and efficiency features such as projection queries.

Here's the full list of magic:

* [Database-level enforcement of unique and unique_together constraints](unique_constraints.md).
* A transparent caching layer for queries which return a single result (`.get` or any query filtering on a unique field
  or unique-together fields). This helps to avoid Datastore
  [consistency issues](https://developers.google.com/appengine/docs/python/datastore/structuring_for_strong_consistency).
* Automatic creation of additional index fields containing pre-manipulated values, so that queries such as `__iexact`
  work out of the box. These index fields are created automatically when you use the queries.  Use
  `settings.GENERATE_SPECIAL_INDEXES_DURING_TESTING` to control whether that automatic creation happens during tests.
* Support for queries which weren't possible with djangoappengine, such as OR queries using `Q` objects.
* A collection of Django model fields which provide useful functionality when using the Datastore.  A `ListField`, `SetField`, `RelatedSetField`, `ShardedCounterField` and `JSONField`.  See the [Djangae Model Fields](fields.md) for full details.

## Roadmap

1.0-beta

 - Support for ancestor queries. Lots of tests

## What Can't It Do?

Due to the limitations of the App Engine Datastore (it being a non-relational database for a start), there are some
things which you still can't do with the Django ORM when using the djangae backend.  The easiest way to find these out
is to just build your app and look out for the `NotSupportedError` exceptions.

### Notable Limitations

Here is a brief list of hard limitations you may encounter when using the Djangae datastore backend:

 - `bulk_create()` is limited to 25 instances if the model has active unique constraints, or the instances being inserted have
   the primary key specified. In other cases the limit is 1000.
 - `filter(field__in=[...])` queries are limited to 100 entries (by default) in the list if `field` is not the primary key
 - `filter(pk__in=[...])` queries are limited to 1000 entries
 - You are limited to a single inequality filter per query, although excluding by primary key is not included in this count
 - Queries without primary key equality filters are not allowed within an `atomic` block
 - Queries with an inequality filter on a field must be ordered first by that field
 - Only 25 individual instances can be retrieved or saved within an `atomic` block, although you can get/save the same entity
   multiple times without increasing the allowed count
 - Primary key values of zero are not allowed
 - Primary key string values must not start with a leading double underscore (`__`)
 - `ManyToManyField` will not work reliably/efficiently - use `RelatedSetField` or `RelatedListField` instead
 - Transactions.  The Datastore has transactions, but they are not "normal" transactions in the SQL sense. [Transactions
  should be done using djangae.db.transactional.atomic](db_backend.md#transactions).
- If unique constraints are enabled, then you are limited to a maximum of 25 unique or unique_together constraints per model (see [Unique Constraint Checking](#unique-constraint-checking)).
- You are also restricted to altering 12 unique field values on an instance in a single save
- `select_related` **does nothing**. It is ignored when specified as joins are not possible on the datastore. This can result in slow
performance on queries which are not designed for the datastore. `prefetch_related` works correctly however.

There are probably more but the list changes regularly as we improve the datastore backend. If you find another limitation not
mentioned above please consider sending a documentation PR.


## Other Considerations

When using the Datastore you should bear in mind its capabilities and limitations. While Djangae allows you to run
Django on the Datastore, it doesn't turn the Datastore into a relational database. There are things which the
datastore is good at (e.g. handling huge bandwidth of reads and writes) and things which it isn't good at
(e.g. counting). Djangae is not a substitute for knowing how to use the
[Datastore](https://developers.google.com/appengine/docs/python/datastore/).

## Using Other Databases

You can use Google Cloud SQL or sqlite (locally) instead of or along side the Datastore.

Note that the Database backend and settings for the Datastore remain the same whether you're in local development or on
App Engine Production, djangae switches between the SDK and the production datastore appropriately.  However, with
Cloud SQL you will need to switch the settings yourself, otherwise you could find yourself developing on your
live database!

Here's an example of how your `DATABASES` might look in settings.py if you're using both Cloud SQL and the Datastore.

```python
from djangae.environment import is_development_environment

DATABASES = {
    'default': {
        'ENGINE': 'djangae.db.backends.appengine'
    }
}

if not is_development_environment():
    DATABASES['sql'] = {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '/cloudsql/YOUR_GOOGLE_CLOUD_PROJECT:YOUR_INSTANCE_NAME',
        'NAME': 'YOUR_DATABASE_NAME',
        'USER': 'root',
    }
else:
    DATABASES['sql'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'development.sqlite3'
    }
```

See the Google documentation for more information on connecting to Cloud SQL via the
[MySQL client](https://developers.google.com/cloud-sql/docs/mysql-client) and from
[external applications](https://developers.google.com/cloud-sql/docs/external).

## Datastore Caching

Djangae has a built-in caching layer, similar to the one built into NDB - only better! You shouldn't even notice the caching layer at work, it's fairly complex and to understand the
behaviour you are best reading through the caching tests. But here's a general overview:

 - There are two layers of caching, the context cache and the memcache cache
 - When possible, if you get/save an entity it will be cached by it's primary key value, and it's unique constraint combinations
 - This protects against HRD inconsistencies in many situations, and it happens automagically
 - The caching layer is heavily tied into the transaction.atomic decorator. If you use the db.RunInTransaction stuff you are going to have a hard time, so don't do that!
 - You can disable the caching by using the `disable_cache` context manager/decorator. `disable_cache` takes two boolean parameters, `context` and `memcache` so you can
   configure which caches you want disabled. Be careful though, don't toggle the caching on and off too much or you might get into trouble (I'm sure there's a situation you can
   break it but I haven't figured out what it is)
 - The context cache has a complex stack structure, when you enter a transaction the stack is pushed, and when you leave a transaction it's popped. This is to ensure the cache
   gives you the right results at the right time
 - The context cache is cleared on each request, and it's thread-local
 - The memcache cache is not cleared, it's global across all instances and so is updated only when a consistent Get/Put outside a transaction is made
 - Entities are evicted from memcache if they are updated inside a transaction (to prevent crazy)

The following settings are available to control the caching:

 - `DJANGAE_CACHE_ENABLED` (default `True`). Setting to False it all off, I really wouldn't suggest doing that!
 - `DJANGAE_CACHE_TIMEOUT_SECONDS` (default `60 * 60`). The length of time stuff should be kept in memcache.

## Datastore Behaviours

The Djangae database backend for the Datastore contains some clever optimisations and integrity checks to make working with the Datastore easier.  This means that in some cases there are behaviours which are either not the same as the Django-on-SQL behaviour or not the same as the default Datastore behaviour. So for clarity, below is a list of statements which are true:

### General Behaviours

* Doing `MyModel.objects.create(primary_key_field=value)` will do an insert, so will explicitly check that an object with that PK doesn't already exist before inserting, and will raise an IntegrityError if it does. This is done in a transaction, so there is no need for any kind of manual transaction or existence checking.
* Doing an `update(field=new_value)` query is transactionally safe (i.e. it uses transactions to ensure that only the specified field is updated), and it also automatically avoids the *Stale objects* issue (see [Eventual consistency](#eventual-consistency) below) so it only updates objects which definitely match the query.  But it still may suffer from the *Missing objects* issue.  See notes about the speed of `update()` queries in the [Speed](#speed) section below.
* A `.distinct()` query is only possible if the query can be done as a projection query (see 'Speed' section below).

### Eventual Consistency

See [App Engine documentation](https://cloud.google.com/appengine/docs/python/datastore/structuring_for_strong_consistency) for background.

The Datastore's eventual consistency behaviour gives us 2 main issues:

* __Stale objects:__ This is where querying for objects by a non-primary key field may return objects which no longer match the query (because they were recently modified) or which were recently deleted.
* __Missing objects:__ This is where querying for objects by a non-primary key may *not* return recently created or recently modified objects which *do* match the query.

There are various solutions and workarounds for these issues.

* If `pk__in` is used in the query (with or without other filters) then the query will be consistent and will returning all matching objects and will not return any non-matching objects.
* Accessing the queryset of a `RelatedSetField` or `RelatedListField` automatically gives you the consistency of a `pk__in` filter (because that's exactly what it's doing underneath).  So `my_obj.my_related_set_field.all()` is consistent.
* To avoid the *Stale objects* issue, you can do an initial `values_list('pk')` query and pass the result to a second query, e.g. `MyModel.objects.filter(size='large', pk__in=list(MyModel.objects.filter(size='large').values_list('pk', flat=True)))`.  Notes:
    - This causes 2 queries, so is slightly slower, although the nested `values_list('pk')` query is fast as it uses a Datastore keys-only.
    - You need to cast the nested PKs query to list, as otherwise Django will try to combine the inner query as a subquery, which the Datastore cannot handle.
    - You need to include the additional filters (in this case `size=large`) in both the inner and outer queries.
    - This technique only avoids the *Stale objects* issue, it does not avoid the *Missing objects* issue.

#### djangae.db.consistency.ensure_instance_consistent

It's very common to need to create a new object, and then redirect to a listing of all objects. This annoyingly falls foul of the
datastore's eventual consistency. As a .all() query is eventually consistent, it's quite likely that the object you just created or updated
either won't be returned, or if it was an update, will show stale data. You can fix this by using [djangae.contrib.consistency](consistency.md) or if you
want a more lightweight approach you can use `djangae.db.consistency.ensure_instance_consistent` like this:

```
queryset = ensure_instance_consistent(MyModel.objects.all(), updated_instance_pk)
```

Be aware though, this will make an additional query for the extra object (although it's very likely to hit the cache). There are also
caveats:

 - If no ordering is specified, the instance will be returned first
 - Only ordering on the queryset is respected, if you are relying on model ordering the instance may be returned in the wrong place (patches welcome!)
 - This causes an extra iteration over the returned queryset once it's retrieved

There is also an equivalent function for ensuring the consistency of multiple items called `ensure_instances_included`.

### Speed

* Using a `pk__in` filter in addition to other filters will usually make the query faster.  This is because Djangae uses the PKs to do a Datastore `Get` operation (which is much faster than a Datastore `Query`) and then does the other filtering in Python.
* Doing `.values('pk')` or `.values_list('pk')` will make a query significantly faster because Djangae performs a keys-only query.
* Doing `.values('other')` type queries will be faster if Djangae is able to perform a Datastore projection query.  This is only possible if:
    - None of the fetched fields are also being filtered on (which would be a weird thing to do anyway).
    - The query is not ordered by primary key.
    - All of the fetched fields are indexed by the Datastore (i.e. are not list/set fields, blob fields or text (as opposed to char) fields).
    - The model has not got concrete parents.
* Doing an `.only('foo')` or `.defer('bar')` with a `pk_in=[...]` filter may not be more efficient. This is because we must perform a projection query for each key, and although we send them over the RPC in batches of 30, the RPC costs may outweigh the savings of a plain old datastore.Get. You should profile and check to see whether using only/defer results in a speed improvement for your use case.
* Due to the way it has to be implemented on the Datastore, an `update()` query is not particularly fast, and other than avoiding calling the `save()` method on each object it doesn't offer much speed advantage over iterating over the objects and modifying them.  However, it does offer significant integrity advantages, see [General behaviours](#general-behaviours) section above.
* Doing filter(pk__in=Something.objects.values_list('pk', flat=True)) will implicitly evaluate the inner query while preparing to run the outer one. This means two queries, not one like SQL would do!
* IN queries and queries with OR branches which aren't filtered on PK result in multiple queries to the datastore. By default you will get an error
  if you exceed 100 IN filters but this is configurable via the `DJANGAE_MAX_QUERY_BRANCHES` setting. Be aware that
  the more IN/OR filters in a query, the slower the query becomes. 100 is already a high value for this setting so
  raising it isn't recommended (it's probably better to rethink your data structure or querying)

## Unique Constraint Checking

**IMPORTANT: Make sure you read and understand this section before configuring your project**

_tl;dr Constraint checking is costly, you might want to disable it globally using `settings.DJANGAE_DISABLE_CONSTRAINT_CHECKS` and re-enable on a per-model basis_

Djangae by default enforces the unique constraints that you define on your models. It does so by creating so called "unique markers" in the datastore.
Unique constraint checks have the following caveats...

 - Unique constraints drastically increase your datastore writes. Djangae needs to create a marker for each unique constraint on each model, for each instance. This means if you have
   one unique field on your model, and you save() Djangae must do two datastore writes (one for the entity, one for the marker)
 - Unique constraints increase your datastore reads. Each time you save an object, Djangae needs to check for the existence of unique markers.
 - Unique constraints slow down your saves(). See above, each time you save, a bunch of stuff needs to happen.
 - Updating instances via the datastore API (NDB, DB, or datastore.Put and friends) will break your unique constraints. Don't do that!
 - Updating instances via the datastore admin will do the same thing, you'll be bypassing the unique marker creation.
 - There is a limit of 25 unique or unique_together constraints per model.

However, unique markers are very powerful when you need to enforce uniqueness. **They are enabled by default** simply because that's the behaviour that Django expects. If you don't want to
use this functionality, you have the following options:

 1. Don't mark fields as unique, or in the meta unique_together - this only works for your models, contrib models will still use unique markers
 2. Disable unique constraints on a per-model basis via the Djangae meta class (again, only works on the model you specify)

        class Djangae:
            disable_constraint_checks = True

 3. Disable constraint checking globally via `settings.DJANGAE_DISABLE_CONSTRAINT_CHECKS`

The `disable_constraint_checks` per-model setting overrides the global `DJANGAE_DISABLE_CONSTRAINT_CHECKS` so if you are concerned about speed/cost then you might want to disable globally and
override on a per-model basis by setting `disable_constraint_checks = False` on models that require constraints.

## On Delete Constraints

In general, Django's emulation of SQL ON DELETE constraints works with djangae on the datastore. Due to eventual consistency however, the constraints can fail. Take care when deleting related objects in quick succession, a PROTECT constraint can wrongly cause a ProtectedError when deleting an object that references a recently deleted one. Constraints can also fail to raise an error if a referencing object was created just prior to deleting the referenced one. Similarly, when using ON CASCADE DELETE (the default behaviour), a newly created referencing object might not be deleted along with the referenced one.

## Transactions

Django's transaction decorators have no effect on the Datastore, which means that when using the Datastore:

 - `django.db.transaction.atomic` and `non_atomic` will have no effect.
 - The `ATOMIC_REQUESTS` and `AUTOCOMMIT` settings in `DATABASES` will have no effect.
 - Django's `get_or_create` will not have the same behaviour when dealing with collisions between threads.  This is because it use's Django's transaction manager rather than Djangae's.
  - If your `get` aspect filters by PK then you should wrap `get_or_create` with `djangae.db.transaction.atomic`.  A collision with another thread will result in a `TransactionFailedError`.
  - If your `get` aspect filters by a unique field or unique-together fields, but not by PK, then (assuming you're using Djangae's unique markers) you won't experience any data corruption, but a collision with another thread will throw an `IntegrityError`.
  - If your `get` aspect does not filter on any unique or unique-together fields then you should fix that.


The following functions are available to manage transactions:

 - `djangae.db.transaction.atomic` - Decorator and Context Manager. Starts a new transaction, accepted `xg`, `indepedendent` and `mandatory` args
 - `djangae.db.transaction.non_atomic` - Decorator and Context Manager. Breaks out of any current transactions so you can run queries outside the transaction
 - `djangae.db.transaction.in_atomic_block` - Returns True if inside a transaction, False otherwise

  **Do not use `google.appengine.ext.db.run_in_transaction` and friends, it will break.**



## Multiple Namespaces


It's possible to create separate "databases" on the datastore via "namespaces". This is supported in Djangae through the normal Django
multiple database support. To configure multiple datastore namespaces, you can add an optional "NAMESPACE" to the DATABASES setting:

```
DATABASES = {
    'default': {
        'ENGINE': 'djangae.db.backends.appengine'
    },
    'archive': {
        'ENGINE': 'djangae.db.backends.appengine'
        'NAMESPACE': 'archive'
    }
}
```

If you do not specify a `NAMESPACE` for a connection, then the Datastore's default namespace will be used (i.e. no namespace).

You can make use of Django's routers, the `using()` method, and the `save(using='...')` in the same way as normal multi-database support.

Cross-namespace foreign keys aren't supported. Also namespaces effect caching keys and unique markers (which are also restricted to a namespace).

## Special Indexes

The App Engine datastore backend handles certain queries which are unsupported natively by adding hidden fields to the datastore instances.
The mechanism for adding these fields and then using them during querying is called "special indexing".

For example, querying for `name__iexact` is not supported by the datastore. In this case Djangae generate an additional entity property with the name
value lower-cased, and then when performing an iexact query, will lower case the lookup value and use the generated column rather than the `name` column.

When you run a query that requires special indexes for the first time, an entry will be added to a generated file called `djangaeidx.yaml`. You will
see this file appear in your project root. From that point on, any entities that are saved will have the additional property added. If a new entry
appears in djangaeidx.yaml, you will need to resave all of your entities of that kind so that they will be returned by query lookups.

### Distributing djangaeidx.yaml

If you are writing a portable app, and your app makes queries which require special indexes, you can ship a custom djangaeidx.yaml in the root of
your Django app. The indexes in this file will be combined with the user's main project djangaeidx.yaml at runtime.

## Migrations

The App Engine Datastore is a schemaless database, so the idea of migrations in the normal Django sense doesn't really apply in the same way.

In order to add a new Django model, you just save an instance of that model, you don't need to tell the database to add a "table" (called a "Kind" in the Datastore) for it.
Similarly, if you want to add a new field to a model, you just add the field and start saving your objects, there's no need to create a new column in the database first.

However, there are some behaviours of the Datastore which mean that in some cases you will want to run some kind of "migration".  The relevant behaviours are:

* If you remove one of your Django models and you want to delete all of the instances, you can't just `DROP` the "table", you must run a task which maps over each object and deletes it.
* If you add a new model field with a default value, that value won't get populated into the database until you re-save each instance.  When you load an instance of the model, the default value will be assigned, but the value won't actually be stored in the database until you re-save the object.  This means that querying for objects with that value will not return any objects that have not been re-saved.  This is true even if the default value is `None` (because the Datastore differentiates between a value being set to `None` and a value not existing at all).
* If you remove a model field, the underlying Datastore entities will still contain the value until they are re-saved.  When you re-save each instance of the model the underlying entity will be overwritten, wiping out the removed field, but if you want to immediately destroy some sensitive data or reduce your used storage quota then simplying removing the field from the model will have no effect.

For these reasons there is a legitimate case for implementing some kind of variant of the Django migration system for Datastore-backed models.  See the [migrations ticket on GitHub](https://github.com/potatolondon/djangae/issues/438) for more info.
