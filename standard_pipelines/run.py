from .assistants.redtrack import start_bots as rt_start_bots

from standard_pipelines import create_app
app = create_app()

if __name__ == "__main__":
    print("__main__")
    rt_start_bots()