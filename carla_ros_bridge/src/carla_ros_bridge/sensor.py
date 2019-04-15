#!/usr/bin/env python

#
# Copyright (c) 2018-2019 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
#
"""
Classes to handle Carla sensors
"""
from abc import abstractmethod

import threading


from carla_ros_bridge.actor import Actor

import carla_ros_bridge.transforms as trans


class Sensor(Actor):

    """
    Actor implementation details for sensors
    """

    @staticmethod
    def create_actor(carla_actor, parent):
        """
        Static factory method to create vehicle actors

        :param carla_actor: carla sensor actor object
        :type carla_actor: carla.Sensor
        :param parent: the parent of the new traffic actor
        :type parent: carla_ros_bridge.Parent
        :return: the created sensor actor
        :rtype: carla_ros_bridge.Sensor or derived type
        """
        if carla_actor.type_id.startswith("sensor.camera"):
            return Camera.create_actor(carla_actor=carla_actor, parent=parent)
        if carla_actor.type_id.startswith("sensor.lidar"):
            return Lidar(carla_actor=carla_actor, parent=parent)
        if carla_actor.type_id.startswith("sensor.other.gnss"):
            return Gnss(carla_actor=carla_actor, parent=parent)
        if carla_actor.type_id.startswith("sensor.other.collision"):
            return CollisionSensor(carla_actor=carla_actor, parent=parent)
        if carla_actor.type_id.startswith("sensor.other.lane_invasion"):
            return LaneInvasionSensor(carla_actor=carla_actor, parent=parent)
        else:
            return Sensor(carla_actor=carla_actor, parent=parent)

    def __init__(self, carla_actor, parent, topic_prefix=None, append_role_name_topic_postfix=True):
        """
        Constructor

        :param carla_actor: carla actor object
        :type carla_actor: carla.Actor
        :param parent: the parent of this
        :type parent: carla_ros_bridge.Parent
        :param topic_prefix: the topic prefix to be used for this actor
        :type topic_prefix: string
        :param append_role_name_topic_postfix: if this flag is set True,
            the role_name of the actor is used as topic postfix
        :type append_role_name_topic_postfix: boolean
        """
        if topic_prefix is None:
            topic_prefix = 'sensor'
        super(Sensor, self).__init__(carla_actor=carla_actor,
                                     parent=parent,
                                     topic_prefix=topic_prefix,
                                     append_role_name_topic_postfix=append_role_name_topic_postfix)

        self.current_sensor_data = None
        self.update_lock = threading.Lock()
        if self.__class__.__name__ == "Sensor":
            self.get_binding().logwarn("Created Unsupported Sensor(id={}, parent_id={}"
                          ", type={}, attributes={}".format(
                              self.get_id(), self.get_parent_id(),
                              self.carla_actor.type_id, self.carla_actor.attributes))
        else:
            self.carla_actor.listen(self._callback_sensor_data)

    def destroy(self):
        """
        Function (override) to destroy this object.

        Stop listening to the carla.Sensor actor.
        Finally forward call to super class.

        :return:
        """
        self.get_binding().logdebug("Destroy Sensor(id={})".format(self.get_id()))
        if self.carla_actor.is_listening:
            self.carla_actor.stop()
        if self.update_lock.acquire():
            self.current_sensor_data = None
        super(Sensor, self).destroy()

    def get_frame_id(self):
        """
        Function (override) to get the frame id of the sensor object.

        Sensor frames respect their respective parent relationship
        within the frame name to prevent from name clashes.

        :return: frame id of the sensor object
        :rtype: string
        """
        return self.parent.get_frame_id() + "/" + super(Sensor, self).get_frame_id()


    def _callback_sensor_data(self, carla_sensor_data):
        """
        Callback function called whenever new sensor data is received

        :param carla_sensor_data: carla sensor data object
        :type carla_sensor_data: carla.SensorData
        """
        if not self.get_binding().is_shutdown():
            if self.update_lock.acquire(False):
                self.current_sensor_data = carla_sensor_data
                self.publish_transform()
                self.sensor_data_updated(carla_sensor_data)
                self.update_lock.release()

    def publish_transform(self):
        """

        """
        self.get_binding().publish_transform(self.get_frame_id(), self.current_sensor_data.transform)

    @abstractmethod
    def sensor_data_updated(self, carla_sensor_data):
        """
        Pure-virtual function to transform the received carla sensor data
        into a corresponding binding message

        :param carla_sensor_data: carla sensor data object
        :type carla_sensor_data: carla.SensorData
        """
        raise NotImplementedError(
            "This function has to be implemented by the derived classes")


# these imports have to be at the end to resolve cyclic dependency
from carla_ros_bridge.camera import Camera  # noqa, pylint: disable=wrong-import-position
from carla_ros_bridge.lidar import Lidar   # noqa, pylint: disable=wrong-import-position
from carla_ros_bridge.gnss import Gnss   # noqa, pylint: disable=wrong-import-position
from carla_ros_bridge.collision_sensor import CollisionSensor   # noqa, pylint: disable=wrong-import-position
from carla_ros_bridge.lane_invasion_sensor import LaneInvasionSensor   # noqa, pylint: disable=wrong-import-position
