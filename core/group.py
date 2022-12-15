class Person:
    
    # étage demandé
    etage_demande = None
    # étage actuel
    etage_actuel = None
    # sens
    sens = None
    # si zéro, appel externe, sinon n° de l'ascenseur concerné
    num_asc = None
    # for capacity reasons.
    weight = None
    # for graphical reasons.
    gender = None
    # for graphical and permission reasons. for example, age below than 12 cannot enter alone.
    age = None
    
    def __init__(self, etage_actuel, etage_demande, weight, gender, age):
        
        self.etage_actuel = etage_actuel
        self.etage_demande = etage_demande

        self.weight = weight
        self.gender = gender
        self.age = age

    def __str__(self):
        return "[Enter: %d, Exit: %d]"%(self.etage_actuel, self.etage_demande)


class People:

    people = None

    weight = None
    # étage actuel
    etage_actuel = None

    def __init__(self, people, etage_actuel):

        self.people = people
        self.etage_actuel = etage_actuel

        for person in people:
            if not isinstance(person, Person):
                self.people = None
                break
            if person.etage_actuel != self.etage_actuel:
                self.people = None
                break
            # sum their weights.
            self.weight = self.weight + person.weight

    def __iter__(self):
        return self.people.__iter__()

    def __len__(self):
        return len(self.people) 

    def __str__(self):
        st = ""
        for p in self.people:
            st = st + str(p) + "\n"
        return st

    def join(self, new):
        self.people.extend(new.people)
        # for p in new:
        #     self.people.append(p)

    def get_weight(self):
        weight = 0
        for p in self.people:
            weight = weight + p.weight
        return weight

    def add_person(self, p):
        self.people.append(p)

    def get_enter_floor(self, floor_nb):
        new_group = People([])
        for p in self.people:
            if p.enter_floor == floor_nb:
                new_group.add_person(p)
        return new_group

    def get_exit_floor(self, floor_nb):
        new_group = People([])
        for p in self.people:
            # print("p: %d = floor: %d"% (p.exit_floor,floor_nb))
            if p.exit_floor == floor_nb:
                new_group.add_person(p)
        return new_group

    def remove_sub_group(self, sub_group):
        lst = []
        for p in self.people:
            if p not in sub_group.people:
                lst.append(p)
        self.people = lst

    def remove_all(self):
        self.people = []

    def get_nb(self):
        return len(self.people)