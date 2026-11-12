# Use an official Python runtime as a parent image
FROM python:3.10.8

# Set the working directory in the container
WORKDIR /app

# Set the PYTHONPATH
ENV PYTHONPATH=/app

RUN mkdir SVC
RUN mkdir SVC/flows
RUN mkdir SVC/flows/flow_OU_S5_02_01
RUN mkdir SVC/common

# Install GDAL dependencies
RUN apt-get update \
    && apt-get install -y \
        python3-gdal \
        gdal-bin \
        libgdal-dev \
        dos2unix \
        build-essential \
        cmake

RUN pip install numpy

RUN pip install GDAL=="$(gdal-config --version).*"

# Install required packages
COPY SVC/flows/flow_OU_S5_02_01/requirements.txt ./SVC/flows/flow_OU_S5_02_01
COPY SVC/flows/flow_OU_S5_02_01/cdsapirc ./SVC/flows/flow_OU_S5_02_01

RUN pip install --no-cache-dir -r ./SVC/flows/flow_OU_S5_02_01/requirements.txt \
    && apt-get update \
    && apt-get install -y libnetcdf-dev libhdf5-serial-dev \
    && pip install --no-cache-dir netcdf4 h5py scipy

RUN pip install cdsapi

# Copy the current directory contents into the container at /app
COPY SVC/flows/flow_OU_S5_02_01 ./SVC/flows/flow_OU_S5_02_01
COPY SVC/flows/common ./SVC/flows/common

# Convert entrypoint.sh to Unix format and give execution permissions
#RUN dos2unix /app/flow_OU_S5_02_01/entrypoint.sh && chmod +x /app/flow_OU_S5_02_01/entrypoint.sh

# Debugging step: list files and permissions in /app/cloud_cover
RUN ls -l /app/SVC/flows/flow_OU_S5_02_01

# Set the entrypoint
#ENTRYPOINT ["/app/lst/entrypoint.sh"]
CMD ["python", "SVC/flows/flow_OU_S5_02_01/flow_s5_02_01.py", "--processing_date", "day/month/year"]