def test_coroutine_has_tornado_attrs():
    import tornado.gen

    def _kittens():
        pass

    kittens = tornado.gen.coroutine(_kittens)

    assert kittens.__wrapped__ is _kittens
    assert kittens.__tornado_coroutine__ is True
