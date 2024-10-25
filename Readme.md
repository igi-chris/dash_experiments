# Overview

## Installing dependencies

I recommend setting up a new virtual environment first as described [here](https://github.com/IGILtd/IGI.ML.Server?tab=readme-ov-file#virtual-environment)

Once the virtual environment is set up and activated, install the dependencies:

```
python -m pip install -r ./requirements-dev.txt
```

## How to run

e.g.
```
python app_housing.py
```

## The apps

These are a collection of experimenst while learning Dash.

The `app_housing.py` and `app_vr_sns` files are based on the short tutoriual fromn the Dash docs: https://dash.plotly.com/tutorial - adding components appropriate for the dataset.

the `app_rainfall.py` is adapted from [Sean's notebook](https://martinigiltd.sharepoint.com/:u:/s/Python/EXs9vzp9KG5Lqgqv-NgOG_MB49tyNual4474AfrlRkuBxw?e=KjujWP) pulling data from the DEFRA API.

