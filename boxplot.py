import matplotlib.pyplot as plt

# Dữ liệu
years = [2010, 2012, 2014, 2016, 2018, 2020, 2022]
population = [1.2, 1.35, 1.5, 1.65, 1.8, 1.95, 2.1]

# Vẽ đồ thị đường
plt.figure()
plt.plot(years, population, marker='o', linestyle='-')

# Gắn nhãn và tiêu đề
plt.xlabel("Năm")
plt.ylabel("Dân số (triệu người)")
plt.title("Tăng trưởng dân số qua các năm")

plt.grid(True)
plt.show()