from mock import Mock, patch

from dynpool import DynamicPoolResizer


def test_no_threads_and_no_conns_grows_minthreads():
    min_threads = 5
    pool = Mock(min=min_threads, max=30, size=0, idle=0, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.grow_value == min_threads
    assert resizer.shrink_value == 0


def test_no_threads_and_waiting_conns_grows_enough():
    maxspare = 10
    pool = Mock(min=5, max=30, size=0, idle=0, qsize=4)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=maxspare)

    # We need to have grown enough threads so that we:
    #  - Have enough to satisfy as many requests in the queue
    #  - Have enough spare threads (between min and max spare).
    assert 9 <= resizer.grow_value <= 14
    assert resizer.shrink_value == 0


def test_no_idle_threads_and_waiting_conns_grows_enough():
    maxspare = 10
    pool = Mock(min=5, max=30, size=4, idle=0, qsize=4)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=maxspare)

    # We need to have grown enough threads so that we:
    #  - Have enough to satisfy as many requests in the queue
    #  - Have enough spare threads (between min and max spare).
    assert 9 <= resizer.grow_value <= 14
    assert resizer.shrink_value == 0


def test_no_idle_threads_and_waiting_conns_grows_enough_respecting_max():
    maxspare = 40
    pool = Mock(min=20, max=40, size=21, idle=0, qsize=4)
    resizer = DynamicPoolResizer(pool, minspare=10, maxspare=maxspare)

    # We need to have grown enough threads so that we:
    #  - Have enough to satisfy as many requests in the queue
    #  - Have enough spare threads (between min and max spare).
    #  - We do not exceed the maximum number of threads.
    assert 14 <= resizer.grow_value <= 40
    assert resizer.shrink_value == 0

def test_no_idle_threads_and_waiting_conns_grows_bigger_than_maxspare():
    maxspare = 40
    pool = Mock(min=20, max=200, size=21, idle=0, qsize=50)
    resizer = DynamicPoolResizer(pool, minspare=10, maxspare=maxspare)

    # We need to have grown enough threads so that we:
    #  - Have enough to satisfy as many requests in the queue
    #  - Have enough spare threads (between min and max spare).
    #  - We do not exceed the maximum number of threads.
    #  - We grow more than maxspare (older versions of dynpool would
    #    limit it to maxspare).
    assert 60 <= resizer.grow_value <= 90
    assert resizer.shrink_value == 0

def test_less_idle_threads_than_minspare_grows():
    idle = 2
    minspare = 5
    pool = Mock(min=5, max=30, size=10, idle=idle, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=minspare, maxspare=10)
    assert resizer.grow_value == minspare - idle
    assert resizer.shrink_value == 0


def test_less_threads_than_minimum_grows():
    size = 3
    minthreads = 5
    pool = Mock(min=minthreads, max=30, size=size, idle=4, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.grow_value == minthreads - size
    assert resizer.shrink_value == 0


def test_more_threads_than_max_doesnt_grow():
    pool = Mock(min=5, max=30, size=100, idle=0, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.grow_value == 0
    assert resizer.shrink_value == 0


def test_more_idle_threads_than_maxspare_shrinks_half():
    pool = Mock(min=5, max=30, size=20, idle=20, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.grow_value == 0
    assert resizer.shrink_value == 15


def test_dont_shrink_when_idle_more_than_maxspare_but_blocked_by_min():
    pool = Mock(min=20, max=40, size=20, idle=20, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=10, maxspare=40)
    assert resizer.grow_value == 0
    assert resizer.shrink_value == 0



def test_normal_thread_counts_without_changes():
    pool = Mock(min=5, max=30, size=20, idle=5, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.grow_value == 0
    assert resizer.shrink_value == 0


def test_more_threads_than_min_and_all_are_idle_without_incoming_conns_shrink():
    pool = Mock(min=5, max=30, size=10, idle=10, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.grow_value == 0
    assert resizer.shrink_value == 5


def test_more_idle_threads_than_maxspread_and_no_incoming_conns_shrink():
    pool = Mock(min=5, max=30, size=15, idle=12, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.grow_value == 0
    assert resizer.shrink_value == 2


def test_more_idle_threads_than_maxspread_and_incoming_conns_shrink():
    pool = Mock(min=5, max=30, size=15, idle=12, qsize=2)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.grow_value == 0
    assert resizer.shrink_value == 2


def test_more_idle_threads_than_minspread_and_incoming_conns_without_changes():
    pool = Mock(min=5, max=30, size=10, idle=7, qsize=3)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.grow_value == 0
    assert resizer.shrink_value == 0


def test_more_idle_threads_than_minspread_and_no_incoming_conns_shrink_half():
    idle = 17
    minspare = 5
    expected_shrinking = 6
    pool = Mock(min=5, max=30, size=28, idle=idle, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=minspare, maxspare=20)
    assert resizer.grow_value == 0
    assert resizer.shrink_value == expected_shrinking


def test_user_should_set_a_max_thread_value():
    lots_of_threads = 1024*1024
    maxspare = 20
    pool = Mock(min=5, max=-1, size=lots_of_threads, idle=0, qsize=100)
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=maxspare)

    # Despite no maximum provided, we should still grow enough threads
    # so that we meet demand - we should be functionally equivalent as
    # if the user had specified a very high max value.
    assert 105 <= resizer.grow_value <= 120
    assert resizer.shrink_value == 0


def test_grow_calls_threadpool_grow():
    pool = Mock()
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    resizer.grow(10)
    pool.grow.assert_called_once_with(10)


def test_shrink_calls_threadpool_shrink():
    pool = Mock()
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    resizer.shrink(10)
    pool.shrink.assert_called_once_with(10)


def test_shrink_sets_lastshrink():
    pool = Mock()
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.lastshrink is None
    resizer.shrink(10)
    assert resizer.lastshrink is not None


def test_new_resizer_can_shrink():
    pool = Mock()
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    assert resizer.lastshrink is None
    assert resizer.can_shrink() is True


def test_can_shrink_past_shrinkfreq():
    shrinkfreq = 3
    pool = Mock()
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10,
                                 shrinkfreq=shrinkfreq)
    resizer.shrink(1)
    resizer.lastshrink -= (shrinkfreq + 1)
    assert resizer.can_shrink() is True


def test_cannot_shrink_before_shrinkfreq():
    shrinkfreq = 3
    pool = Mock()
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10,
                                 shrinkfreq=shrinkfreq)
    resizer.shrink(1)
    resizer.lastshrink -= (shrinkfreq - 1)
    assert resizer.can_shrink() is False

# If we have one more thread than minspare, then avoid shrinking.
#
# Otherwise, as soon as a request comes in and is allocated to a thread,
# we will have to create a new thread to satisfy the "minspare"
# requirement. It makes more sense to have a spare thread hanging
# around, rather than having a thread fluttering in and out of
# existence.
def test_no_spare_fluttering_thread():
    pool = Mock(min=1, max=30, size=4, idle=3, qsize=0)
    resizer = DynamicPoolResizer(pool, minspare=2, maxspare=10)
    assert resizer.shrink_value == 0

@patch.multiple('dynpool.DynamicPoolResizer',
                grow_value=3, shrink_value=0,
                grow=Mock(), shrink=Mock(), can_shrink=Mock())
def test_run_with_grow_value_calls_grow_and_not_shrink():
    pool = Mock()
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    resizer.run()
    resizer.grow.assert_called_once_with(3)
    assert not resizer.can_shrink.called
    assert not resizer.shrink.called


@patch.multiple('dynpool.DynamicPoolResizer',
                grow_value=0, shrink_value=3,
                grow=Mock(), shrink=Mock(), can_shrink=Mock())
def test_run_with_shrink_value_calls_shrink_and_not_grow():
    pool = Mock()
    resizer = DynamicPoolResizer(pool, minspare=5, maxspare=10)
    resizer.run()
    assert not resizer.grow.called
    assert resizer.can_shrink.called
    resizer.shrink.assert_called_once_with(3)
