Why Solid Node
==============

When designing a mechanical project with Free Software, there are some technologies available that allow parametric design, using source code to create solid structures. There's OpenScad, which uses it's own scripting language, and on top of it there is Solid Python, which allows modelling for OpenScad using Python language. Python also has CadQuery, which is more powerful and flexible for complex designs, but has a steeper learning curve. When picking which technology to use, one should consider the libraries available, and a complex project might need to assemble pieces that come from different libraries. Openscad has a native animation system that allows developing projects with moving parts, but it soon gets very slow as project grows.

Solid Node come as a framework to join all these underlying technologies together and solve performance bottlenecks. It's inspired by a web development culture, which uses frameworks like Django, React and Angular, that monitors filesystem for changes and shows results automatically. Solid Node proposes an architecture that allows building of pieces as they change, being able to handle a lot of moving parts.

Solid Node also provides testing capabilities. Prototyping can take a lot of time and generate a lot of garbage, and this can be substantially reduced by being able to logically test connections between components before producing anything.

Solid Node is Free Software, released under the AGPLv3. This mean that any project using it is bound to the AGPLv3. As digital manufacturing technologies, like 3D printing, become popular, distribution of source code can greatly increase goods lifetime and reduce waste generation. Free Software modeling and source code distribution should become an industry standard, and this project is one more step towards that.
