import matplotlib.pyplot as plt
import matplotlib.patches as patches

fg = "#CCCCCC"
bg = "#333333"

colors = [bg, fg]

for i in range(101):
    sizes = [100 - i, i]

    fig = plt.figure(figsize=(1.28, 1.28), dpi=100)
    ax = plt.gca()
    ax.pie(sizes, startangle=90, colors=colors)
    ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.

    plt.savefig("{}.png".format(i), transparent=True)
    plt.close("all")

sizes = [100, 0]
fig = plt.figure(figsize=(1.28, 1.28), dpi=100)
ax = plt.gca()
ax.pie(sizes, startangle=90, colors=colors)
ax.axis("equal")
for x in [-0.65, -0.15, 0.35]:
    rect = patches.Rectangle((x, -0.15), 0.3, 0.3, linewidth=0, facecolor=fg)
    ax.add_patch(rect)
plt.savefig("unknown.png", transparent=True)
