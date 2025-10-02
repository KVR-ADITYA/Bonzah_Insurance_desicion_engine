import pandas as pd
import numpy as np
import os
import sys

def main():
    df1 = pd.read_csv('./auto_bi.csv')
    df2 = pd.read_csv('./auto_collision.csv')
    df3 = pd.read_csv('./datacar.csv')

    print(df1.columns)
    print(df2.columns)
    print(df3.columns)


if __name__ == "__main__":
    main()