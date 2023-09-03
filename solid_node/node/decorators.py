def property_as_number(method):

    def new_method(self):
        number_promise = method(self)
        return self.as_number(number_promise)

    return property(new_method)
