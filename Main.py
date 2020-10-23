import matplotlib.pyplot as plt
import numpy as np
import random
import string
import tkinter as tk
from tkinter import ttk, font, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class Board:
    def __init__(self):
        self.board_rows = 10
        self.board_columns = 10
        self.ships = {'Carrier': 5, 'Battleship': 4, 'Cruiser': 3, 'Submarine': 3, 'Destroyer': 2}  # ship_name: ship_size
        self.ship_status = dict(zip(list(self.ships.keys()), [True] * len(self.ships.keys())))  # Every ship at the beginning is "alive"


class ShotManager(Board):
    def __init__(self):
        super().__init__()
        self.empty_fields_coords = set()
        self.occupied_fields_coords = []
        self.boost_start_index = 0
        self.boost_active = False
        self.boost_values = {'horizontal': 0, 'vertical': 0}

    def register_new_shot(self, coords, status, sunken_ship_name=None):
        if status == 'Miss':
            self.empty_fields_coords.add(coords)
        else:
            if sunken_ship_name is not None:
                self.ship_status[sunken_ship_name] = False

            self.occupied_fields_coords.append(coords)
            self.is_boost_active()
            self.transfer_fields_from_sunken_ship_to_empty_fields()
            self.change_boost_starting_index()
            self.set_boost_values()

    def is_boost_active(self):
        self.boost_active = len(self.occupied_fields_coords) != sum([value for key, value in self.ships.items() if not self.ship_status[key]])

    def transfer_fields_from_sunken_ship_to_empty_fields(self):
        if not self.boost_active and len(self.occupied_fields_coords[self.boost_start_index:]):
            for field in self.occupied_fields_coords[self.boost_start_index:]:
                self.empty_fields_coords.add(field)

    def change_boost_starting_index(self):
        if not self.boost_active:
            self.boost_start_index = len(self.occupied_fields_coords)

    def set_boost_values(self):
        if self.boost_active:
            self.boost_values = {'horizontal': 25, 'vertical': 25}
            if len(self.occupied_fields_coords[self.boost_start_index:]) > 1:
                occupied_fields_row_coords = [field[0] for field in self.occupied_fields_coords[self.boost_start_index:]]
                occupied_fields_row_coords.sort()

                occupied_fields_column_coords = [field[1] for field in self.occupied_fields_coords[self.boost_start_index:]]
                occupied_fields_column_coords.sort()

                if occupied_fields_row_coords[0] == occupied_fields_row_coords[-1]:
                    self.boost_values['horizontal'] = 50
                elif occupied_fields_column_coords[0] == occupied_fields_column_coords[-1]:
                    self.boost_values['vertical'] = 50
        else:
            self.boost_values = {'horizontal': 0, 'vertical': 0}


class HeatMap(Board):
    def __init__(self, ship_name, sm_object, show_heat_map=False):
        super().__init__()
        self.sm_object = sm_object
        self.ship_name = ship_name
        self.ship_size = self.ships[ship_name]

        self.heat_map = np.zeros((self.board_rows, self.board_columns), dtype=float)
        if self.sm_object.ship_status[ship_name]:
            self.create_heat_map()
        if show_heat_map:
            self.show_heat_map()

    def create_heat_map(self):
        for i in range(self.board_rows):
            for j in range(self.board_columns - self.ship_size + 1):
                check_excluded_list = [int((i, j + k) not in self.sm_object.empty_fields_coords) for k in range(self.ship_size)]
                if all(check_excluded_list):
                    self.heat_map[i, j: j + self.ship_size] += check_excluded_list

        for i in range(self.board_columns):
            for j in range(self.board_rows - self.ship_size + 1):
                check_excluded_list = [int((j + k, i) not in self.sm_object.empty_fields_coords) for k in range(self.ship_size)]
                if all(check_excluded_list):
                    self.heat_map[j: j + self.ship_size, i] += check_excluded_list

        for occupied_field in self.sm_object.occupied_fields_coords:
            i, j = occupied_field
            self.heat_map[i, j] = 0

        if self.sm_object.boost_active:
            for occupied_field in self.sm_object.occupied_fields_coords[self.sm_object.boost_start_index:]:
                i, j = occupied_field
                if self.sm_object.boost_values.get('vertical', False):
                    if i:
                        if self.heat_map[i-1, j]:
                            self.heat_map[i-1, j] += self.sm_object.boost_values['vertical']

                    if i != self.board_rows - 1:
                        if self.heat_map[i+1, j]:
                            self.heat_map[i+1, j] += self.sm_object.boost_values['vertical']

                if self.sm_object.boost_values.get('horizontal', False):
                    if j:
                        if self.heat_map[i, j-1]:
                            self.heat_map[i, j-1] += self.sm_object.boost_values['horizontal']

                    if j != self.board_columns - 1:
                        if self.heat_map[i, j+1]:
                            self.heat_map[i, j+1] += self.sm_object.boost_values['horizontal']

        self.heat_map /= sum(self.heat_map.flatten())
        self.heat_map *= self.ship_size

    def show_heat_map(self):
        fig, ax = plt.subplots()

        plt.imshow(self.heat_map, cmap='plasma')
        plt.title(self.ship_name)
        for i in range(self.board_rows):
            for j in range(self.board_columns):
                ax.text(j, i, f'{round(100 * self.heat_map[i, j], 2)}%', ha="center", va="center", color="k")


class Battleships:
    def __init__(self, sm_object=ShotManager()):
        self.sm_object = sm_object
        self.heat_maps = [HeatMap(ship_name, sm_object).heat_map for ship_name in sm_object.ships.keys()]

        self.row_dictionary, self.column_dictionary = self.create_coordinates_dictionary_for_user()

    def create_coordinates_dictionary_for_user(self):
        dictionary_keys = [i for i in range(max(self.sm_object.board_rows, self.sm_object.board_columns))]
        return dict(zip(dictionary_keys, [letter for letter in string.ascii_uppercase][:self.sm_object.board_rows])), dict(zip(dictionary_keys, [str(i + 1) for i in range(self.sm_object.board_columns)]))

    def update_heat_maps(self):
        self.heat_maps = [HeatMap(ship_name, self.sm_object).heat_map for ship_name in self.sm_object.ships.keys()]

    def make_decision(self):
        current_heat_map_maximum_value = 0
        decision = None
        for heat_map in self.heat_maps:
            maximum_value = max(heat_map.flatten())
            if current_heat_map_maximum_value < maximum_value:
                current_heat_map_maximum_value = maximum_value
                indexes_with_maximum_value = [(i, j) for i in range(len(heat_map)) for j in range(len(heat_map[i])) if heat_map[i, j] == current_heat_map_maximum_value]
                decision = random.choice(indexes_with_maximum_value)

        return decision

    def format_decision(self, decision):
        return f'{self.row_dictionary[decision[0]]}{self.column_dictionary[decision[1]]}'

    def run(self, iteration=1):
        def check_user_input(decision_, status_, sunken_ship_, iteration_):
            if status_ == '':
                tk.messagebox.showerror('Error!', 'Response field is empty!')
            elif status_ == 'Hit & Sunk' and sunken_ship_ == '':
                tk.messagebox.showerror('Error!', 'Please select which ship has been sunk!')
            else:
                quit_program()
                finish_turn(decision_, status_, sunken_ship_, iteration_)

        def finish_turn(decision_, status_, sunken_ship_, iteration_):
            if sunken_ship_ == '':
                sunken_ship_ = None
            self.sm_object.register_new_shot(decision_, status_, sunken_ship_name=sunken_ship_)
            self.update_heat_maps()
            iteration_ += 1
            self.run(iteration_)

        def combo_box_sunken_ship_mode(*args):
            if status.get() == "Hit & Sunk":
                combo_box_sunken_ship.config(state="readonly")
            else:
                sunken_ship.set("")
                combo_box_sunken_ship.config(state="disabled")

        def quit_program():
            plt.close()
            root.quit()
            root.destroy()
            
        root = tk.Tk()
        root.protocol("WM_DELETE_WINDOW", quit_program)
        root.title('Battleships')
        decision = None

        tk.Label(root, text='Battleships', font=font.Font(family='Helvetica', size=14, weight='bold')).pack()
        if any(self.sm_object.ship_status.values()):
            tk.Label(root, text=f'Round: {iteration}\n', font=font.Font(family='Helvetica', size=12, weight='normal')).pack()

            decision = self.make_decision()

            tk.Label(root, text=f'Computer move: {self.format_decision(decision)}\n', font=font.Font(family='Helvetica', size=12, weight='normal')).pack()

            frame = tk.Frame(root)
            tk.Label(frame, text='Response: ', font=font.Font(family='Helvetica', size=12, weight='normal')).pack(side=tk.LEFT)
            status = tk.StringVar()
            status.trace("w", combo_box_sunken_ship_mode)
            combo_box_status = ttk.Combobox(frame, textvariable=status, state='readonly')
            combo_box_status['values'] = ('Miss', 'Hit', 'Hit & Sunk')
            combo_box_status.pack(side=tk.LEFT)

            tk.Label(frame, text='  ').pack(side=tk.LEFT)

            tk.Label(frame, text='Sunken ship: ', font=font.Font(family='Helvetica', size=12, weight='normal')).pack(side=tk.LEFT)
            sunken_ship = tk.StringVar()
            combo_box_sunken_ship = ttk.Combobox(frame, textvariable=sunken_ship, state='readonly')
            combo_box_sunken_ship['values'] = tuple([key for key in self.sm_object.ships.keys() if self.sm_object.ship_status[key]])
            combo_box_sunken_ship.config(state="disabled")
            combo_box_sunken_ship.pack(side=tk.LEFT)

            frame.pack()

            tk.Label(root, text='').pack()
            button = tk.Button(root, text='SEND', bd=4, font=font.Font(family='Helvetica', size=12, weight='normal'), command=lambda: [check_user_input(decision, status.get(), sunken_ship.get(), iteration)])
            button.pack()
        else:
            tk.Label(root, text=f'Round: {iteration-1}\n', font=font.Font(family='Helvetica', size=12, weight='normal')).pack()

        canvas = FigureCanvasTkAgg(self.get_current_board_figure(decision), master=root)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.window_config(root)
        tk.mainloop()

    def get_current_board_figure(self, decision=None, cell_dimension=0.1):
        plt.clf()
        cells = np.array([['  ' for _ in range(self.sm_object.board_columns + 1)] for _ in range(self.sm_object.board_rows + 1)])

        for i in range(1, len(cells)):
            cells[i, 0] = self.row_dictionary[i-1]
        for j in range(1, len(cells[0])):
            cells[0, j] = self.column_dictionary[j-1]

        for empty_field in self.sm_object.empty_fields_coords:
            i, j = empty_field
            cells[i+1, j+1] = 'O'
        for occupied_field in self.sm_object.occupied_fields_coords:
            i, j = occupied_field
            cells[i+1, j+1] = 'X'
        if decision is not None:
            cells[decision[0] + 1, decision[1] + 1] = '+'

        current_board = plt.table(cells, loc='center', rowLoc='center', colLoc='center', cellLoc='center')

        cell_dict = current_board.get_celld()
        for i in range(len(cells)):
            for j in range(len(cells[i])):
                cell_dict[(i, j)].set_height(cell_dimension)
                cell_dict[(i, j)].set_width(cell_dimension)
                if not i or not j:
                    cell_dict[(i, j)].set_color('white')
                    cell_dict[(i, j)].get_text().set_color('black')
                else:
                    cell_dict[(i, j)].set_color('dodgerblue')
                cell_dict[(i, j)].set_edgecolor('black')

        for empty_field in self.sm_object.empty_fields_coords:
            i, j = empty_field
            cell_dict[i+1, j+1].get_text().set_color('white')
        for occupied_field in self.sm_object.occupied_fields_coords:
            i, j = occupied_field
            cell_dict[i+1, j+1].get_text().set_color('red')
        if decision is not None:
            cell_dict[decision[0] + 1, decision[1] + 1].get_text().set_color('yellow')

        current_board.auto_set_font_size(False)
        current_board.set_fontsize(20)
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)

        plt.box(on=None)

        return plt.gcf()

    @staticmethod
    def window_config(window, width_adjuster=0.85, height_adjuster=0.55):
        window.attributes('-topmost', 1)
        window.update()
        window.attributes('-topmost', 0)
        window.focus_force()
        window.update()
        window.geometry('%dx%d+%d+%d' % (window.winfo_width(), window.winfo_height(), width_adjuster * ((window.winfo_screenwidth() / 2) - (window.winfo_width() / 2)), height_adjuster * ((window.winfo_screenheight() / 2) - (window.winfo_height() / 2))))


if __name__ == '__main__':
    Battleships().run()
