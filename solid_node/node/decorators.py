def property_as_number(method):
    """Use this decorator to convert a OpenScad property to a number"""

    def new_method(self):
        number_promise = method(self)
        return self.as_number(number_promise)

    return property(new_method)
